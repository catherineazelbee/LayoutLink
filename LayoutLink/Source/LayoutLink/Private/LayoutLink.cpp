// LayoutLink.cpp

#include "LayoutLink.h"

#include "LevelEditor.h"
#include "ToolMenus.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Framework/MultiBox/MultiBoxBuilder.h"

#include "IDesktopPlatform.h"
#include "DesktopPlatformModule.h"
#include "Interfaces/IMainFrameModule.h"

#include "Interfaces/IPluginManager.h"
#include "Modules/ModuleManager.h"
#include "Misc/Paths.h"
#include "Misc/DateTime.h"
#include "Misc/MessageDialog.h"
#include "Misc/ConfigCacheIni.h"

#include "IPythonScriptPlugin.h"
#include "HAL/PlatformFilemanager.h"
#include "Styling/AppStyle.h"
#include "Styling/CoreStyle.h"

#define LOCTEXT_NAMESPACE "FLayoutLinkModule"

// ---------------------------
// Tab + Menu Registration
// ---------------------------

static const FName LayoutLinkTabName(TEXT("LayoutLink"));

void FLayoutLinkModule::StartupModule()
{
#if WITH_EDITOR
	UToolMenus::RegisterStartupCallback(
		FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FLayoutLinkModule::RegisterMenus));

	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(LayoutLinkTabName,
		FOnSpawnTab::CreateRaw(this, &FLayoutLinkModule::OnSpawnPluginTab))
		.SetDisplayName(LOCTEXT("TabTitle", "LayoutLink"))
		.SetTooltipText(LOCTEXT("TooltipText", "USD Pipeline for Maya/Unreal"))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

	// Load user settings (paths)
	LoadSettings();
#endif
}

void FLayoutLinkModule::ShutdownModule()
{
#if WITH_EDITOR
	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(LayoutLinkTabName);
	UToolMenus::UnRegisterStartupCallback(this);
	UToolMenus::UnregisterOwner(this);
#endif
}

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
	
	// Add to Window menu
	{
		UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
		FToolMenuSection& Section = Menu->FindOrAddSection("LayoutLink");
		Section.AddMenuEntry(
			"OpenLayoutLink",
			LOCTEXT("OpenLayoutLink", "LayoutLink"),
			LOCTEXT("OpenLayoutLink_Tooltip", "Open the LayoutLink panel"),
			FSlateIcon(),
			FUIAction(FExecuteAction::CreateRaw(this, &FLayoutLinkModule::PluginButtonClicked)));
	}
	
	// Add toolbar button
	{
		UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
		FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("PluginTools");
		Section.AddEntry(FToolMenuEntry::InitToolBarButton(
			"LayoutLink",
			FUIAction(FExecuteAction::CreateRaw(this, &FLayoutLinkModule::PluginButtonClicked)),
			LOCTEXT("LayoutLinkButton", "LayoutLink"),
			LOCTEXT("LayoutLinkButtonTooltip", "Open LayoutLink USD Pipeline"),
			FSlateIcon(FAppStyle::GetAppStyleSetName(), "LevelEditor.Tabs.Outliner")
		));
	}
}
#endif

// ---------------------------
// Settings Persistence
// ---------------------------

void FLayoutLinkModule::LoadSettings()
{
	// Sensible defaults if missing
	FString DefaultAsset   = TEXT("C:/SharedUSD/assets/unreal");
	FString DefaultLayouts = TEXT("C:/SharedUSD/layouts/unreal_layouts");

	GConfig->GetString(TEXT("/Script/LayoutLink"), TEXT("AssetLibraryPath"), AssetLibraryPath, GEditorPerProjectIni);
	GConfig->GetString(TEXT("/Script/LayoutLink"), TEXT("LayoutExportDir"),  LayoutExportDir,  GEditorPerProjectIni);

	if (AssetLibraryPath.IsEmpty()) AssetLibraryPath = DefaultAsset;
	if (LayoutExportDir.IsEmpty())  LayoutExportDir  = DefaultLayouts;
}

void FLayoutLinkModule::SaveSettings()
{
	GConfig->SetString(TEXT("/Script/LayoutLink"), TEXT("AssetLibraryPath"), *AssetLibraryPath, GEditorPerProjectIni);
	GConfig->SetString(TEXT("/Script/LayoutLink"), TEXT("LayoutExportDir"),  *LayoutExportDir,  GEditorPerProjectIni);
	GConfig->Flush(false, GEditorPerProjectIni);
}

// ---------------------------
// UI: Tab
// ---------------------------

TSharedRef<SDockTab> FLayoutLinkModule::OnSpawnPluginTab(const FSpawnTabArgs& Args)
{
	const FSlateFontInfo Bold12  = FAppStyle::GetFontStyle("BoldFont");
	const FSlateFontInfo BoldTitle = FCoreStyle::GetDefaultFontStyle("Bold", 16);

	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
	[
		SNew(SScrollBox)

		// =====================
		// TITLE
		// =====================
		+ SScrollBox::Slot()
		.Padding(10.0f, 10.0f)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("Header", "LayoutLink"))
			.Font(BoldTitle)
			.Justification(ETextJustify::Center)
		]

		// =====================
		// SETTINGS SECTION
		// =====================
		+ SScrollBox::Slot()
		.Padding(10.f, 5.f, 10.f, 5.f)
		[
			SNew(SSeparator)
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 10.f, 10.f, 8.f)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("SettingsHeader", "Settings"))
			.Font(Bold12)
		]

		// Asset Library row
		+ SScrollBox::Slot()
		.Padding(10.f, 3.f, 10.f, 3.f)
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.f, 0.f, 10.f, 0.f)
			.VAlign(VAlign_Center)
			[
				SNew(SBox)
				.MinDesiredWidth(100.f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("AssetLibrary", "Asset Library:"))
				]
			]

			+ SHorizontalBox::Slot()
			.FillWidth(1.0f)
			.VAlign(VAlign_Center)
			[
				SNew(SEditableTextBox)
				.Text_Lambda([this]() { return FText::FromString(AssetLibraryPath); })
				.OnTextCommitted_Lambda([this](const FText& NewText, ETextCommit::Type)
				{
					AssetLibraryPath = NewText.ToString();
					SaveSettings();
					if (StatusTextWidget.IsValid())
					{
						StatusTextWidget->SetText(FText::FromString(
							FString::Printf(TEXT("Asset Library updated:\n%s"), *AssetLibraryPath)));
					}
				})
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(5.f, 0.f, 0.f, 0.f)
			.VAlign(VAlign_Center)
			[
				SNew(SButton)
				.Text(LOCTEXT("BrowseAsset", "Browse..."))
				.OnClicked_Raw(this, &FLayoutLinkModule::OnBrowseAssetLibrary)
			]
		]

		// Layout Export row
		+ SScrollBox::Slot()
		.Padding(10.f, 3.f, 10.f, 10.f)
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.f, 0.f, 10.f, 0.f)
			.VAlign(VAlign_Center)
			[
				SNew(SBox)
				.MinDesiredWidth(100.f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("LayoutExport", "Layout Export:"))
				]
			]

			+ SHorizontalBox::Slot()
			.FillWidth(1.0f)
			.VAlign(VAlign_Center)
			[
				SNew(SEditableTextBox)
				.Text_Lambda([this]() { return FText::FromString(LayoutExportDir); })
				.OnTextCommitted_Lambda([this](const FText& NewText, ETextCommit::Type)
				{
					LayoutExportDir = NewText.ToString();
					SaveSettings();
					if (StatusTextWidget.IsValid())
					{
						StatusTextWidget->SetText(FText::FromString(
							FString::Printf(TEXT("Layout Export updated:\n%s"), *LayoutExportDir)));
					}
				})
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(5.f, 0.f, 0.f, 0.f)
			.VAlign(VAlign_Center)
			[
				SNew(SButton)
				.Text(LOCTEXT("BrowseLayout", "Browse..."))
				.OnClicked_Raw(this, &FLayoutLinkModule::OnBrowseLayoutExport)
			]
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 0.f, 10.f, 10.f)
		[
			SNew(SSeparator)
		]

		// =====================
		// EXPORT TO MAYA
		// =====================
		+ SScrollBox::Slot()
		.Padding(10.f, 10.f, 10.f, 8.f)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("ExportHeader", "Export to Maya"))
			.Font(Bold12)
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 3.f, 10.f, 5.f)
		[
			SNew(SButton)
			.Text(LOCTEXT("ExportMeshLib", "Export Mesh Library (Selected)"))
			.ToolTipText(LOCTEXT("ExportMeshTip", "Export selected static meshes to USD asset library"))
			.OnClicked_Raw(this, &FLayoutLinkModule::OnExportMeshLibraryClicked)
			.ContentPadding(FMargin(10.f, 8.f))
			.ButtonColorAndOpacity(FLinearColor(0.13f, 0.59f, 0.95f, 1.0f))  // Blue color
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 3.f, 10.f, 10.f)
		[
			SNew(SButton)
			.Text(LOCTEXT("ExportLayout", "Export Layout (Selected)"))
			.ToolTipText(LOCTEXT("ExportLayoutTip", "Export selected actors as USD layout with references"))
			.OnClicked_Raw(this, &FLayoutLinkModule::OnExportButtonClicked)
			.ContentPadding(FMargin(10.f, 8.f))
			.ButtonColorAndOpacity(FLinearColor(0.3f, 0.69f, 0.31f, 1.0f))  // Green color
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 0.f, 10.f, 10.f)
		[
			SNew(SSeparator)
		]

		// =====================
		// IMPORT FROM MAYA
		// =====================
		+ SScrollBox::Slot()
		.Padding(10.f, 10.f, 10.f, 8.f)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("ImportHeader", "Import from Maya"))
			.Font(Bold12)
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 3.f, 10.f, 10.f)
		[
			SNew(SButton)
			.Text(LOCTEXT("ImportLayout", "Import Layout from Maya"))
			.ToolTipText(LOCTEXT("ImportLayoutTip", "Import USD layout from Maya (creates USD Stage Actor)"))
			.OnClicked_Raw(this, &FLayoutLinkModule::OnImportButtonClicked)
			.ContentPadding(FMargin(10.f, 8.f))
			.ButtonColorAndOpacity(FLinearColor(1.0f, 0.6f, 0.0f, 1.0f))  // Orange color
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 0.f, 10.f, 10.f)
		[
			SNew(SSeparator)
		]

		// =====================
		// STATUS LOG
		// =====================
		+ SScrollBox::Slot()
		.Padding(10.f, 10.f, 10.f, 5.f)
		[
			SNew(STextBlock)
			.Text(LOCTEXT("StatusHeader", "Status Log"))
			.Font(Bold12)
		]

		+ SScrollBox::Slot()
		.Padding(10.f, 3.f, 10.f, 10.f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
			.Padding(5.f)
			[
				SAssignNew(StatusTextWidget, STextBlock)
				.Text_Lambda([this]()
				{
					const FString Msg = FString::Printf(
						TEXT("Ready\n\nAsset Library: %s\nLayout Export: %s\n\nSelect actors and use export buttons."),
						*AssetLibraryPath, *LayoutExportDir);
					return FText::FromString(Msg);
				})
				.AutoWrapText(true)
			]
		]
	];
}

// ---------------------------
// Browse handlers
// ---------------------------

FReply FLayoutLinkModule::OnBrowseAssetLibrary()
{
	IDesktopPlatform* Desktop = FDesktopPlatformModule::Get();
	if (!Desktop) return FReply::Handled();

	void* ParentWindowHandle = nullptr;
	if (FModuleManager::Get().IsModuleLoaded("MainFrame"))
	{
		IMainFrameModule& MainFrame = FModuleManager::LoadModuleChecked<IMainFrameModule>("MainFrame");
		TSharedPtr<SWindow> W = MainFrame.GetParentWindow();
		if (W.IsValid() && W->GetNativeWindow().IsValid())
		{
			ParentWindowHandle = W->GetNativeWindow()->GetOSWindowHandle();
		}
	}

	FString OutDir;
	const bool bPicked = Desktop->OpenDirectoryDialog(
		ParentWindowHandle,
		TEXT("Choose Asset Library Folder"),
		AssetLibraryPath,
		OutDir);

	if (bPicked)
	{
		AssetLibraryPath = OutDir;
		SaveSettings();
		if (StatusTextWidget.IsValid())
		{
			StatusTextWidget->SetText(FText::FromString(
				FString::Printf(TEXT("Asset Library set to:\n%s"), *OutDir)));
		}
	}
	return FReply::Handled();
}

FReply FLayoutLinkModule::OnBrowseLayoutExport()
{
	IDesktopPlatform* Desktop = FDesktopPlatformModule::Get();
	if (!Desktop) return FReply::Handled();

	void* ParentWindowHandle = nullptr;
	if (FModuleManager::Get().IsModuleLoaded("MainFrame"))
	{
		IMainFrameModule& MainFrame = FModuleManager::LoadModuleChecked<IMainFrameModule>("MainFrame");
		TSharedPtr<SWindow> W = MainFrame.GetParentWindow();
		if (W.IsValid() && W->GetNativeWindow().IsValid())
		{
			ParentWindowHandle = W->GetNativeWindow()->GetOSWindowHandle();
		}
	}

	FString OutDir;
	const bool bPicked = Desktop->OpenDirectoryDialog(
		ParentWindowHandle,
		TEXT("Choose Layout Export Folder"),
		LayoutExportDir,
		OutDir);

	if (bPicked)
	{
		LayoutExportDir = OutDir;
		SaveSettings();
		if (StatusTextWidget.IsValid())
		{
			StatusTextWidget->SetText(FText::FromString(
				FString::Printf(TEXT("Layout Export set to:\n%s"), *OutDir)));
		}
	}
	return FReply::Handled();
}

// ---------------------------
// Export Buttons
// ---------------------------

FReply FLayoutLinkModule::OnExportMeshLibraryClicked()
{
	// Call Python: mesh_export.export_selected_meshes_library(asset_lib_dir)
	const TSharedPtr<IPlugin> ThisPlugin = IPluginManager::Get().FindPlugin(TEXT("LayoutLink"));
	if (!ThisPlugin.IsValid())
	{
		FMessageDialog::Open(EAppMsgType::Ok, LOCTEXT("PluginMissing", "LayoutLink plugin not found."));
		return FReply::Handled();
	}

	const FString PyPath = ThisPlugin->GetContentDir() / TEXT("Python");
	const FString Command = FString::Printf(
		TEXT("import sys; sys.path.insert(0, r'%s'); ")
		TEXT("import mesh_export as me; ")
		TEXT("print('=== Mesh Export Starting ==='); ")
		TEXT("print('Asset Library:', r'%s'); ")
		TEXT("result = me.export_selected_meshes_library(r'%s'); ")
		TEXT("print('Export result:', result)"),
		*PyPath, *AssetLibraryPath, *AssetLibraryPath);

	if (IPythonScriptPlugin::Get())
	{
		IPythonScriptPlugin::Get()->ExecPythonCommand(*Command);
	}

	if (StatusTextWidget.IsValid())
	{
		StatusTextWidget->SetText(FText::FromString(
			FString::Printf(TEXT("Mesh Library Export requested.\nAsset Library: %s"), *AssetLibraryPath)));
	}
	return FReply::Handled();
}

FReply FLayoutLinkModule::OnExportButtonClicked()
{
	// Simple default filename
	const FString DefaultName = TEXT("unreal_layout.usda");
	const FString DefaultFullPath = FPaths::Combine(LayoutExportDir, DefaultName);

	// Show Save As dialog
	IDesktopPlatform* Desktop = FDesktopPlatformModule::Get();
	FString Chosen;
	if (Desktop)
	{
		void* Parent = nullptr;
		if (FModuleManager::Get().IsModuleLoaded("MainFrame"))
		{
			IMainFrameModule& MainFrame = FModuleManager::LoadModuleChecked<IMainFrameModule>("MainFrame");
			TSharedPtr<SWindow> W = MainFrame.GetParentWindow();
			if (W.IsValid() && W->GetNativeWindow().IsValid())
				Parent = W->GetNativeWindow()->GetOSWindowHandle();
		}

		TArray<FString> OutFiles;
		const bool bOk = Desktop->SaveFileDialog(
			Parent,
			TEXT("Save USD Layout"),
			LayoutExportDir,
			DefaultName,
			TEXT("USD ASCII (*.usda)|*.usda|USD Binary (*.usd)|*.usd|USD Crate (*.usdc)|*.usdc"),
			EFileDialogFlags::None,
			OutFiles);

		Chosen = (bOk && OutFiles.Num() > 0) ? OutFiles[0] : DefaultFullPath;
	}
	else
	{
		Chosen = DefaultFullPath;
	}

	ExportUSDFile(Chosen);
	return FReply::Handled();
}

// ---------------------------
// Import Button
// ---------------------------

FReply FLayoutLinkModule::OnImportButtonClicked()
{
	// Choose a USD file
	IDesktopPlatform* Desktop = FDesktopPlatformModule::Get();
	if (!Desktop) return FReply::Handled();

	void* Parent = nullptr;
	if (FModuleManager::Get().IsModuleLoaded("MainFrame"))
	{
		IMainFrameModule& MainFrame = FModuleManager::LoadModuleChecked<IMainFrameModule>("MainFrame");
		TSharedPtr<SWindow> W = MainFrame.GetParentWindow();
		if (W.IsValid() && W->GetNativeWindow().IsValid())
			Parent = W->GetNativeWindow()->GetOSWindowHandle();
	}

	TArray<FString> Files;
	const bool bOk = Desktop->OpenFileDialog(
		Parent,
		TEXT("Open USD Layout"),
		LayoutExportDir,
		TEXT(""),
		TEXT("USD Files (*.usd;*.usda;*.usdc)|*.usd;*.usda;*.usdc"),
		EFileDialogFlags::None,
		Files);

	if (bOk && Files.Num() > 0)
	{
		const FString Path = Files[0];
		ImportUSDFile(Path);
		
		if (StatusTextWidget.IsValid())
		{
			StatusTextWidget->SetText(FText::FromString(
				FString::Printf(TEXT("Import requested:\n%s\n\nCheck Output Log for details."), *Path)));
		}
	}
	return FReply::Handled();
}

// ---------------------------
// Export / Import helpers
// ---------------------------

void FLayoutLinkModule::ExportUSDFile(const FString& FilePath)
{
	const TSharedPtr<IPlugin> ThisPlugin = IPluginManager::Get().FindPlugin(TEXT("LayoutLink"));
	if (!ThisPlugin.IsValid())
	{
		FMessageDialog::Open(EAppMsgType::Ok, LOCTEXT("PluginMissing2", "LayoutLink plugin not found."));
		return;
	}

	const FString PyPath = ThisPlugin->GetContentDir() / TEXT("Python");

	const FString Command = FString::Printf(
		TEXT("import sys; sys.path.insert(0, r'%s'); ")
		TEXT("import layout_export as le; ")
		TEXT("print('=== Layout Export Starting ==='); ")
		TEXT("print('Layout file:', r'%s'); ")
		TEXT("print('Asset library:', r'%s'); ")
		TEXT("res = le.export_selected_to_usd(r'%s', r'%s'); ")
		TEXT("print('Export result:', res)"),
		*PyPath, *FilePath, *AssetLibraryPath, *FilePath, *AssetLibraryPath);

	if (IPythonScriptPlugin::Get())
	{
		IPythonScriptPlugin::Get()->ExecPythonCommand(*Command);
	}

	if (StatusTextWidget.IsValid())
	{
		StatusTextWidget->SetText(FText::FromString(
			FString::Printf(TEXT("Export requested:\n%s\nAsset Library: %s\n\nCheck Output Log for details."),
				*FilePath, *AssetLibraryPath)));
	}
}

void FLayoutLinkModule::ImportUSDFile(const FString& FilePath)
{
	// Import USD file from Maya - spawn USD Stage Actor
	UE_LOG(LogTemp, Warning, TEXT("Importing USD layout from Maya: %s"), *FilePath);
	
	const TSharedPtr<IPlugin> ThisPlugin = IPluginManager::Get().FindPlugin(TEXT("LayoutLink"));
	if (!ThisPlugin.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("Could not find LayoutLink plugin"));
		if (StatusTextWidget.IsValid())
		{
			StatusTextWidget->SetText(FText::FromString(TEXT("Error: LayoutLink plugin not found.")));
		}
		return;
	}

	const FString PyPath = ThisPlugin->GetContentDir() / TEXT("Python");
	
	// Call the layout_import.py script to actually spawn the USD Stage Actor
	FString PythonCommand = FString::Printf(
		TEXT("import sys; sys.path.insert(0, r'%s'); ")
		TEXT("import layout_import; ")
		TEXT("result = layout_import.import_usd_from_maya(r'%s'); ")
		TEXT("print('Import result:', result)"),
		*PyPath,
		*FilePath
	);
	
	// Execute Python script to spawn USD Stage Actor
	if (IPythonScriptPlugin::Get())
	{
		IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonCommand);
	}
	
	// Update status
	if (StatusTextWidget.IsValid())
	{
		StatusTextWidget->SetText(FText::FromString(
			FString::Printf(TEXT("USD Stage Actor created!\n\nFile: %s\n\nCheck the Outliner for 'MayaLayoutImport'\nand Output Log for details."), *FilePath)));
	}
}

FString FLayoutLinkModule::ReadMetadataFromUSD(const FString& FilePath)
{
	// Uses Python to read metadata (more stable than C++)
	UE_LOG(LogTemp, Warning, TEXT("Reading metadata via Python: %s"), *FilePath);
	
	// Get plugin directory
	TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("LayoutLink"));
	if (!Plugin.IsValid())
	{
		return TEXT("Could not find plugin");
	}
	
	FString PythonScriptPath = FPaths::Combine(Plugin->GetBaseDir(), TEXT("Content/Python"));
	
	// Build Python command to read and format metadata
	FString PythonScript = FString::Printf(
		TEXT("import sys\n")
		TEXT("sys.path.append(r'%s')\n")
		TEXT("from pxr import Sdf\n")
		TEXT("import metadata_utils\n")
		TEXT("layer = Sdf.Layer.FindOrOpen(r'%s')\n")
		TEXT("metadata = metadata_utils.read_layoutlink_metadata(layer) if layer else None\n")
		TEXT("result = metadata_utils.format_metadata_string(metadata)\n")
		TEXT("print('METADATA_RESULT:', result)\n"),
		*PythonScriptPath,
		*FilePath
	);
	
	// Execute and capture output
	IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonScript);
	
	// For now, return a simple message
	return TEXT("Metadata read via Python (check Output Log)");
}

IMPLEMENT_MODULE(FLayoutLinkModule, LayoutLink)

#undef LOCTEXT_NAMESPACE