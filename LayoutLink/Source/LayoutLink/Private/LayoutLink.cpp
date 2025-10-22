// Copyright Epic Games, Inc. All Rights Reserved.

#include "LayoutLink.h"
#include "LayoutLinkStyle.h"
#include "LayoutLinkCommands.h"
#include "LevelEditor.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "ToolMenus.h"

// USD includes - must be wrapped with special macros
#include "USDIncludesStart.h"
    #include "pxr/usd/usd/stage.h"
    #include "pxr/usd/sdf/layer.h"
#include "USDIncludesEnd.h"

// Unreal USD includes
#include "USDStageActor.h"
#include "USDStageImporter.h"

// File dialog
#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"
#include "Interfaces/IMainFrameModule.h"

// For metadata reading
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

// Additional Slate widgets
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SScrollBox.h"

static const FName LayoutLinkTabName("LayoutLink");

#define LOCTEXT_NAMESPACE "FLayoutLinkModule"

void FLayoutLinkModule::StartupModule()
{
	// This code will execute after your module is loaded into memory; the exact timing is specified in the .uplugin file per-module

	FLayoutLinkStyle::Initialize();
	FLayoutLinkStyle::ReloadTextures();

	FLayoutLinkCommands::Register();

	PluginCommands = MakeShareable(new FUICommandList);

	PluginCommands->MapAction(
		FLayoutLinkCommands::Get().OpenPluginWindow,
		FExecuteAction::CreateRaw(this, &FLayoutLinkModule::PluginButtonClicked),
		FCanExecuteAction());

	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FLayoutLinkModule::RegisterMenus));

	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(LayoutLinkTabName, FOnSpawnTab::CreateRaw(this, &FLayoutLinkModule::OnSpawnPluginTab)).SetDisplayName(LOCTEXT("FLayoutLinkTabTitle", "LayoutLink")).SetMenuType(ETabSpawnerMenuType::Hidden);
}

void FLayoutLinkModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.

	UToolMenus::UnRegisterStartupCallback(this);

	UToolMenus::UnregisterOwner(this);

	FLayoutLinkStyle::Shutdown();

	FLayoutLinkCommands::Unregister();

	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(LayoutLinkTabName);
}

TSharedRef<SDockTab> FLayoutLinkModule::OnSpawnPluginTab(const FSpawnTabArgs& SpawnTabArgs)
{
    return SNew(SDockTab)
        .TabRole(ETabRole::NomadTab)
        [
            // Main vertical container (stacks widgets top to bottom)
            SNew(SVerticalBox)
            
            // === HEADER ===
            + SVerticalBox::Slot()
            .AutoHeight()
            .Padding(10.0f)
            [
                SNew(STextBlock)
                .Text(FText::FromString("Import Layout from Maya"))
                .Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))
                .Justification(ETextJustify::Center)
            ]
            
            // === BIG IMPORT BUTTON ===
            + SVerticalBox::Slot()
            .AutoHeight()
            .Padding(10.0f)
            [
                SNew(SButton)
                .Text(FText::FromString("IMPORT USD FROM MAYA"))
                .OnClicked_Raw(this, &FLayoutLinkModule::OnImportButtonClicked)
            ]
            
            // === STATUS TEXT ===
            + SVerticalBox::Slot()
            .FillHeight(1.0f)
            .Padding(10.0f)
            [
                SNew(SScrollBox) // allows scrolling if text too long
				+ SScrollBox:: Slot()
				[
					// Save reference to this widget so we can update it
					SAssignNew(StatusTextWidget, STextBlock) // SAssig stores it in StatusTextWidget
					.Text(FText::FromString("Click Import to load USD files from Maya \n\nShared Folder: C:/SharedUSD/unreal_exports"))
				]
            ]
        ];
}

void FLayoutLinkModule::PluginButtonClicked()
{
	FGlobalTabmanager::Get()->TryInvokeTab(LayoutLinkTabName);
}

void FLayoutLinkModule::RegisterMenus()
{
	// Owner will be used for cleanup in call to UToolMenus::UnregisterOwner
	FToolMenuOwnerScoped OwnerScoped(this);

	{
		UToolMenu *Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
		{
			FToolMenuSection &Section = Menu->FindOrAddSection("WindowLayout");
			Section.AddMenuEntryWithCommandList(FLayoutLinkCommands::Get().OpenPluginWindow, PluginCommands);
		}
	}

	{
		UToolMenu *ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
		{
			FToolMenuSection &Section = ToolbarMenu->FindOrAddSection("PluginTools");
			{
				FToolMenuEntry &Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FLayoutLinkCommands::Get().OpenPluginWindow));
				Entry.SetCommandList(PluginCommands);
			}
		}
	}
}
FReply FLayoutLinkModule::OnImportButtonClicked()
{
    UE_LOG(LogTemp, Warning, TEXT("=== Opening File Dialogue ==="));

	// STEP 1: Get the desktop platform module for file dialogues
	// Provides cross-platform file browsing
	IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
	if (!DesktopPlatform)
	{
		UE_LOG(LogTemp, Warning, TEXT("Could not get desktop platform module"));
		return FReply::Handled();
	}

	// STEP 2: Get the main Unreal window to use as parent for dialog
	const void* ParentWindowHandle = FSlateApplication::Get().FindBestParentWindowHandleForDialogue(nullptr);

	// STEP 3: Setup file dialog parameters
	TArray<FString> OutFiles; // Array to store selected file paths
	const FString DialogTitle = TEXT("Import USD from Maya");
	const FString DefaultPath = TEXT("C:/SharedUSD/unreal_exports"); // start directory
	const FString DefaultFile = TEXT(""); // no default file
	const FString FileTypes = TEXT("USD Files (*.usd;*.usda,*.usdc)|*.usd,*usda,*usdc"); // start directory
	const uint32 Flags = 0; // dialog flags (0=default)

	// STEP 4: Show the file dialog (opens Windows file browser)
	bool bFileSelected = DesktopPlatform->OpenFileDialog(
		ParentWindowHandle,
		DialogTitle,
		DefaultPath,
		DefaultFile,
		FileTypes,
		Flags,
		OutFiles // selected files go here
	)

	// STEP 5: Check if user selected a file (or cancelled)
	if (bFileSelected && OutFiles.Num() > 0) 
	{
		// user selected a file
		FString SelectedFile = OutFiles[0];
		UE_LOG(LogTemp, Warning, TEXT("User selected file %s"), *SelectedFile);

		// update status text
		if (StatusTextWidget.IsValid())
		{
			FString StatusMessage = FString::Printf(
				TEXT("Importing: %s\n\nPlease wait...")
				*FPaths::GetCleanFilename(SelectedFile)
			);
			StatusTextWidget->SetText(FText::FromString(StatusMessage));
		}

		// STEP 6: Import the selected USD file
		ImportUSDFile(SelectedFile);
	} else {
		// user cancelled message
		UE_LOG(LogTemp, Warning, TEXT("User cancelled file selection"), *SelectedFile);
	}

    return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FLayoutLinkModule, LayoutLink)