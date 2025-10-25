// LayoutLink.cpp

#include "LayoutLink.h"

#include "Framework/Application/SlateApplication.h"
#include "Misc/Paths.h"
#include "Interfaces/IMainFrameModule.h"
#if WITH_EDITOR
#include "Editor.h"
#include "LevelEditor.h"
#include "ToolMenus.h"
#endif

#include "LayoutLinkCommands.h"
#include "LayoutLinkStyle.h"

#include "Framework/Docking/TabManager.h"
#include "Framework/Commands/UICommandList.h"
#include "Containers/StringConv.h"
#include "Widgets/SBoxPanel.h"
#include "Styling/CoreStyle.h"

#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SScrollBox.h"

#include "USDIncludesStart.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/sdf/layer.h"
#include "USDIncludesEnd.h"

#include "USDStageActor.h"
#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"

static const FName LayoutLinkTabName("LayoutLink");

#define LOCTEXT_NAMESPACE "FLayoutLinkModule"

void FLayoutLinkModule::StartupModule()
{
	FLayoutLinkStyle::Initialize();
	FLayoutLinkStyle::ReloadTextures();

	FLayoutLinkCommands::Register();

	PluginCommands = MakeShareable(new FUICommandList);

	PluginCommands->MapAction(
		FLayoutLinkCommands::Get().OpenPluginWindow,
		FExecuteAction::CreateRaw(this, &FLayoutLinkModule::PluginButtonClicked),
		FCanExecuteAction());

#if WITH_EDITOR
	UToolMenus::RegisterStartupCallback(
		FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FLayoutLinkModule::RegisterMenus));

	FGlobalTabmanager::Get()
		->RegisterNomadTabSpawner(LayoutLinkTabName,
			FOnSpawnTab::CreateRaw(this, &FLayoutLinkModule::OnSpawnPluginTab))
		.SetDisplayName(LOCTEXT("FLayoutLinkTabTitle", "LayoutLink"))
		.SetMenuType(ETabSpawnerMenuType::Hidden);
#endif
}

void FLayoutLinkModule::ShutdownModule()
{
#if WITH_EDITOR
	UToolMenus::UnRegisterStartupCallback(this);
	UToolMenus::UnregisterOwner(this);
	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(LayoutLinkTabName);
#endif

	FLayoutLinkStyle::Shutdown();
	FLayoutLinkCommands::Unregister();
}

#if WITH_EDITOR
TSharedRef<SDockTab> FLayoutLinkModule::OnSpawnPluginTab(const FSpawnTabArgs& SpawnTabArgs)
{
	return SNew(SDockTab).TabRole(ETabRole::NomadTab)[
		SNew(SVerticalBox)

		+ SVerticalBox::Slot().AutoHeight().Padding(10.0f)
		[
			SNew(STextBlock)
			.Text(FText::FromString("Import Layout from Maya"))
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))
			.Justification(ETextJustify::Center)
		]

		+ SVerticalBox::Slot().AutoHeight().Padding(10.0f)
		[
			SNew(SButton)
			.Text(FText::FromString("IMPORT USD FROM MAYA"))
			.OnClicked_Raw(this, &FLayoutLinkModule::OnImportButtonClicked)
		]

		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(10.0f)
		[
			SNew(SScrollBox)
			+ SScrollBox::Slot()
			[
				SAssignNew(StatusTextWidget, STextBlock)
				.Text(FText::FromString("Click Import to load USD files from Maya \n\nShared Folder: C:/SharedUSD/unreal_exports"))
				.AutoWrapText(true)
			]
		]
	];
}
#endif

void FLayoutLinkModule::PluginButtonClicked()
{
#if WITH_EDITOR
	FGlobalTabmanager::Get()->TryInvokeTab(LayoutLinkTabName);
#endif
}

#if WITH_EDITOR
void FLayoutLinkModule::RegisterMenus()
{
	FToolMenuOwnerScoped OwnerScoped(this);

	{
		UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
		FToolMenuSection& Section = Menu->FindOrAddSection("WindowLayout");
		Section.AddMenuEntryWithCommandList(FLayoutLinkCommands::Get().OpenPluginWindow, PluginCommands);
	}

	{
		UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
		FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("PluginTools");
		FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FLayoutLinkCommands::Get().OpenPluginWindow));
		Entry.SetCommandList(PluginCommands);
	}
}
#endif

FReply FLayoutLinkModule::OnImportButtonClicked()
{
	UE_LOG(LogTemp, Warning, TEXT("=== Opening File Dialogue ==="));

	IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
	if (!DesktopPlatform)
	{
		UE_LOG(LogTemp, Warning, TEXT("Could not get desktop platform module"));
		return FReply::Handled();
	}

	// ✅ FIXED: Replaced deprecated FindBestParentWindowHandleForDialogue
	void* ParentWindowHandle = nullptr;
	IMainFrameModule& MainFrame = FModuleManager::LoadModuleChecked<IMainFrameModule>("MainFrame");
	TSharedPtr<SWindow> MainWindow = MainFrame.GetParentWindow();
	if (MainWindow.IsValid() && MainWindow->GetNativeWindow().IsValid())
	{
		ParentWindowHandle = MainWindow->GetNativeWindow()->GetOSWindowHandle();
	}

	TArray<FString> OutFiles;
	const FString DialogTitle = TEXT("Import USD from Maya");
	const FString DefaultPath = TEXT("C:/SharedUSD/unreal_exports");
	const FString DefaultFile = TEXT("");
	const FString FileTypes = TEXT("USD Files (*.usd;*.usda;*.usdc)|*.usd;*.usda;*.usdc");
	const uint32 Flags = 0;

	bool bFileSelected = DesktopPlatform->OpenFileDialog(
		ParentWindowHandle,
		DialogTitle,
		DefaultPath,
		DefaultFile,
		FileTypes,
		Flags,
		OutFiles
	);

	if (bFileSelected && OutFiles.Num() > 0)
	{
		FString SelectedFile = OutFiles[0];
		UE_LOG(LogTemp, Warning, TEXT("User selected file %s"), *SelectedFile);

		if (StatusTextWidget.IsValid())
		{
			FString StatusMessage = FString::Printf(TEXT("Importing: %s\n\nPlease wait..."), *FPaths::GetCleanFilename(SelectedFile));
			StatusTextWidget->SetText(FText::FromString(StatusMessage));
		}

		ImportUSDFile(SelectedFile);
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("User cancelled file selection"));
	}

	return FReply::Handled();
}

void FLayoutLinkModule::ImportUSDFile(const FString& FilePath)
{
	UE_LOG(LogTemp, Warning, TEXT("=== Starting USD Import ==="));
	UE_LOG(LogTemp, Warning, TEXT("File: %s"), *FilePath);

	if (!FPaths::FileExists(FilePath))
	{
		UE_LOG(LogTemp, Error, TEXT("File does not exist: %s"), *FilePath);

		if (StatusTextWidget.IsValid())
		{
			StatusTextWidget->SetText(FText::FromString(TEXT("ERROR: File not found")));
		}
		return;
	}

#if !WITH_EDITOR
	UE_LOG(LogTemp, Error, TEXT("USD import only works in the Editor."));
	return;
#endif

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World)
	{
		UE_LOG(LogTemp, Error, TEXT("No world found!"));
		return;
	}

	FString MetadataInfo = ReadMetadataFromUSD(FilePath);
	UE_LOG(LogTemp, Warning, TEXT("Metadata: %s"), *MetadataInfo);

	FActorSpawnParameters SpawnParams;
	SpawnParams.Name = FName("MayaLayoutImport");

	// ✅ FIXED: Replaced FRotator::ZeroVector with FRotator::ZeroRotator
	AUsdStageActor* StageActor = World->SpawnActor<AUsdStageActor>(
		AUsdStageActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);

	if (!StageActor)
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to spawn USD Stage Actor"));
		if (StatusTextWidget.IsValid())
		{
			StatusTextWidget->SetText(FText::FromString(TEXT("ERROR: Failed to create USD Stage Actor")));
		}
		return;
	}

	StageActor->SetRootLayer(*FilePath);
	StageActor->SetTime(0.0f);

	if (StatusTextWidget.IsValid())
	{
		FString SuccessMessage = FString::Printf(TEXT("✓ Import Successful!\n\nFile: %s\n\n%s\n\nUSD Stage Actor created in World Outliner"),
			*FPaths::GetCleanFilename(FilePath), *MetadataInfo);
		StatusTextWidget->SetText(FText::FromString(SuccessMessage));
		UE_LOG(LogTemp, Warning, TEXT("=== USD Import Complete ==="));
	}
}

FString FLayoutLinkModule::ReadMetadataFromUSD(const FString& FilePath)
{
	UE_LOG(LogTemp, Warning, TEXT("Reading metadata from: %s"), *FilePath);

	std::string FilePathStd = TCHAR_TO_UTF8(*FilePath);
	pxr::SdfLayerRefPtr Layer = pxr::SdfLayer::FindOrOpen(FilePathStd);

	if (!Layer)
	{
		UE_LOG(LogTemp, Warning, TEXT("Could not open USD layer for metadata"));
		return TEXT("No metadata found");
	}

	pxr::VtDictionary CustomData = Layer->GetCustomLayerData();

	if (CustomData.empty())
	{
		UE_LOG(LogTemp, Warning, TEXT("No custom layer data found"));
		return TEXT("No LayoutLink metadata");
	}

	FString MetadataString = TEXT("=== Maya Export Info ===\n");

	auto GetStringValue = [&CustomData](const std::string& Key) -> FString {
		if (CustomData.count(Key) > 0)
		{
			pxr::VtValue Value = CustomData[Key];
			if (Value.IsHolding<std::string>())
			{
				std::string StrValue = Value.Get<std::string>();
				return FString(UTF8_TO_TCHAR(StrValue.c_str()));
			}
		}
		return TEXT("N/A");
	};

	FString Timestamp = GetStringValue("layoutlink_timestamp");
	FString Artist = GetStringValue("layoutlink_artist");
	FString App = GetStringValue("layoutlink_app");
	FString Operation = GetStringValue("layoutlink_operation");
	FString Version = GetStringValue("layoutlink_version");

	MetadataString += FString::Printf(TEXT("Artist: %s\n"), *Artist);
	MetadataString += FString::Printf(TEXT("Exported: %s\n"), *Timestamp);
	MetadataString += FString::Printf(TEXT("From: %s\n"), *App);
	MetadataString += FString::Printf(TEXT("Version: %s"), *Version);

	UE_LOG(LogTemp, Warning, TEXT("Metadata extracted successfully"));
	return MetadataString;
}

#undef LOCTEXT_NAMESPACE
IMPLEMENT_MODULE(FLayoutLinkModule, LayoutLink)