// LayoutLink.cpp
// Main implementation file for the LayoutLink plugin
// Handles USD import from Maya and (soon) export to Maya

#include "LayoutLink.h"

// For finding plugin directory
#include "Interfaces/IPluginManager.h"

// Unreal framework includes
#include "Framework/Application/SlateApplication.h"
#include "Misc/Paths.h"
#include "Interfaces/IMainFrameModule.h"

#if WITH_EDITOR
#include "Editor.h"
#include "LevelEditor.h"
#include "ToolMenus.h"
#endif

// Plugin-specific includes
#include "LayoutLinkCommands.h"
#include "LayoutLinkStyle.h"

// UI framework includes
#include "Framework/Docking/TabManager.h"
#include "Framework/Commands/UICommandList.h"
#include "Containers/StringConv.h"
#include "Widgets/SBoxPanel.h"
#include "Styling/CoreStyle.h"

// Slate UI widgets
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SScrollBox.h"

// Unreal selection and export
#include "Selection.h"

// Unreal's USD integration
#include "USDStageActor.h"

// File dialog system
#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"

// Python integration
#include "IPythonScriptPlugin.h"
#include "PythonScriptTypes.h"

// Tab name for the LayoutLink window
static const FName LayoutLinkTabName("LayoutLink");

#define LOCTEXT_NAMESPACE "FLayoutLinkModule"

// ============================================================================
// MODULE LIFECYCLE
// ============================================================================

void FLayoutLinkModule::StartupModule()
{
    // Called when the plugin loads
    // Sets up UI, commands, and registers the tab
    
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
    // Called when the plugin unloads
    // Cleanup all registered UI elements
    
#if WITH_EDITOR
    UToolMenus::UnRegisterStartupCallback(this);
    UToolMenus::UnregisterOwner(this);
    FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(LayoutLinkTabName);
#endif
    
    FLayoutLinkStyle::Shutdown();
    FLayoutLinkCommands::Unregister();
}

// ============================================================================
// UI CONSTRUCTION
// ============================================================================

#if WITH_EDITOR
TSharedRef<SDockTab> FLayoutLinkModule::OnSpawnPluginTab(const FSpawnTabArgs& SpawnTabArgs)
{
    // This function builds the UI inside the LayoutLink window
    // Called whenever the user opens the LayoutLink tab
    
    return SNew(SDockTab)
        .TabRole(ETabRole::NomadTab)
        [
            // Main vertical container - stacks all widgets from top to bottom
            SNew(SVerticalBox)
            
            // ============================================================
            // HEADER TEXT
            // ============================================================
            + SVerticalBox::Slot()
            .AutoHeight()  // Only takes the height it needs
            .Padding(10.0f)  // 10 pixels of padding around the widget
            [
                SNew(STextBlock)
                .Text(FText::FromString("LayoutLink - Maya to Unreal"))
                .Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))
                .Justification(ETextJustify::Center)
            ]
            
            // ============================================================
            // IMPORT BUTTON (Green)
            // ============================================================
            + SVerticalBox::Slot()
            .AutoHeight()
            .Padding(10.0f)
            [
                SNew(SButton)
                .Text(FText::FromString("IMPORT USD FROM MAYA"))
                .OnClicked_Raw(this, &FLayoutLinkModule::OnImportButtonClicked)
            ]
            
            // ============================================================
            // EXPORT BUTTON (Blue) - NEW!
            // ============================================================
            + SVerticalBox::Slot()
            .AutoHeight()
            .Padding(10.0f)
            [
                SNew(SButton)
                .Text(FText::FromString("EXPORT TO MAYA"))
                .ButtonColorAndOpacity(FLinearColor(0.2f, 0.6f, 1.0f))  // Blue tint
                .OnClicked_Raw(this, &FLayoutLinkModule::OnExportButtonClicked)
            ]
            
            // ============================================================
            // STATUS TEXT AREA (with scrolling)
            // ============================================================
            + SVerticalBox::Slot()
            .FillHeight(1.0f)  // Takes all remaining vertical space
            .Padding(10.0f)
            [
                SNew(SScrollBox)  // Allows scrolling if text is long
                + SScrollBox::Slot()
                [
                    // SAssignNew saves a pointer to this widget so we can update it later
                    SAssignNew(StatusTextWidget, STextBlock)
                    .Text(FText::FromString("Click Import to load USD files from Maya\n\nShared Folder: C:/SharedUSD/unreal_exports"))
                    .AutoWrapText(true)  // Wrap long lines
                ]
            ]
        ];
}
#endif

// ============================================================================
// MENU REGISTRATION
// ============================================================================

void FLayoutLinkModule::PluginButtonClicked()
{
    // Called when user clicks the LayoutLink toolbar button
    // Opens the LayoutLink tab
    
#if WITH_EDITOR
    FGlobalTabmanager::Get()->TryInvokeTab(LayoutLinkTabName);
#endif
}

#if WITH_EDITOR
void FLayoutLinkModule::RegisterMenus()
{
    // Adds LayoutLink to Unreal's menus and toolbar
    
    FToolMenuOwnerScoped OwnerScoped(this);
    
    // Add to Window menu
    {
        UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
        FToolMenuSection& Section = Menu->FindOrAddSection("WindowLayout");
        Section.AddMenuEntryWithCommandList(FLayoutLinkCommands::Get().OpenPluginWindow, PluginCommands);
    }
    
    // Add to toolbar
    {
        UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
        FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("PluginTools");
        FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FLayoutLinkCommands::Get().OpenPluginWindow));
        Entry.SetCommandList(PluginCommands);
    }
}
#endif

// ============================================================================
// IMPORT FUNCTIONALITY (Maya → Unreal)
// ============================================================================

FReply FLayoutLinkModule::OnImportButtonClicked()
{
    // Called when user clicks "IMPORT USD FROM MAYA" button
    // Opens file dialog to select USD file, then imports it
    
    UE_LOG(LogTemp, Warning, TEXT("=== Opening File Dialog ==="));
    
    // STEP 1: Get the file dialog system
    IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
    if (!DesktopPlatform)
    {
        UE_LOG(LogTemp, Error, TEXT("Could not get desktop platform module"));
        return FReply::Handled();
    }
    
    // STEP 2: Get parent window for the dialog
    void* ParentWindowHandle = nullptr;
    IMainFrameModule& MainFrame = FModuleManager::LoadModuleChecked<IMainFrameModule>("MainFrame");
    TSharedPtr<SWindow> MainWindow = MainFrame.GetParentWindow();
    if (MainWindow.IsValid() && MainWindow->GetNativeWindow().IsValid())
    {
        ParentWindowHandle = MainWindow->GetNativeWindow()->GetOSWindowHandle();
    }
    
    // STEP 3: Configure file dialog
    TArray<FString> OutFiles;  // Will store selected file paths
    const FString DialogTitle = TEXT("Import USD from Maya");
    const FString DefaultPath = TEXT("C:/SharedUSD/maya_exports");  // Where Maya exports to
    const FString DefaultFile = TEXT("");
    const FString FileTypes = TEXT("USD Files (*.usd;*.usda;*.usdc)|*.usd;*.usda;*.usdc");
    const uint32 Flags = 0;
    
    // STEP 4: Show the file browser
    bool bFileSelected = DesktopPlatform->OpenFileDialog(
        ParentWindowHandle,
        DialogTitle,
        DefaultPath,
        DefaultFile,
        FileTypes,
        Flags,
        OutFiles
    );
    
    // STEP 5: Process user selection
    if (bFileSelected && OutFiles.Num() > 0)
    {
        // User selected a file
        FString SelectedFile = OutFiles[0];
        UE_LOG(LogTemp, Warning, TEXT("User selected file: %s"), *SelectedFile);
        
        // Update status text to show we're importing
        if (StatusTextWidget.IsValid())
        {
            FString StatusMessage = FString::Printf(
                TEXT("Importing: %s\n\nPlease wait..."),
                *FPaths::GetCleanFilename(SelectedFile)
            );
            StatusTextWidget->SetText(FText::FromString(StatusMessage));
        }
        
        // Actually import the file
        ImportUSDFile(SelectedFile);
    }
    else
    {
        // User cancelled
        UE_LOG(LogTemp, Warning, TEXT("User cancelled file selection"));
    }
    
    return FReply::Handled();
}

void FLayoutLinkModule::ImportUSDFile(const FString& FilePath)
{
    // Uses Python script to import USD from Maya
    
    UE_LOG(LogTemp, Warning, TEXT("=== Calling Python Import Script ==="));
    UE_LOG(LogTemp, Warning, TEXT("File: %s"), *FilePath);
    
    // Get plugin directory
    TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("LayoutLink"));
    if (!Plugin.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("Could not find LayoutLink plugin"));
        return;
    }
    
    FString PythonScriptPath = FPaths::Combine(Plugin->GetBaseDir(), TEXT("Content/Python"));
    
    // Build Python command
    FString PythonScript = FString::Printf(
        TEXT("import sys; "
             "sys.path.append(r'%s'); "
             "import layout_import; "
             "result = layout_import.import_usd_from_maya(r'%s'); "
             "print('Import result:', result)"),
        *PythonScriptPath,
        *FilePath
    );
    
    // Execute Python
    FPythonCommandEx PythonCommand;
    PythonCommand.Command = PythonScript;
    PythonCommand.ExecutionMode = EPythonCommandExecutionMode::ExecuteStatement;
    
    bool bSuccess = IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonCommand.Command);
    
    if (bSuccess)
    {
        UE_LOG(LogTemp, Warning, TEXT("Python import completed"));
        
        if (StatusTextWidget.IsValid())
        {
            StatusTextWidget->SetText(FText::FromString(
                TEXT("Import Successful!\n\nUSD Stage Actor created.\nCheck World Outliner for 'MayaLayoutImport'")
            ));
        }
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Python import failed"));
        
        if (StatusTextWidget.IsValid())
        {
            StatusTextWidget->SetText(FText::FromString(
                TEXT("ERROR: Python import failed!\n\nCheck Output Log for details.")
            ));
        }
    }
}

// ============================================================================
// EXPORT FUNCTIONALITY (Unreal → Maya)
// ============================================================================

FReply FLayoutLinkModule::OnExportButtonClicked()
{
    // Called when user clicks "EXPORT TO MAYA" button
    // Exports selected Unreal actors to USD for Maya import
    
    UE_LOG(LogTemp, Warning, TEXT("=== Starting Export to Maya ==="));
    
    // STEP 1: Check if anything is selected
    USelection* SelectedActors = GEditor->GetSelectedActors();
    if (!SelectedActors || SelectedActors->Num() == 0)
    {
        UE_LOG(LogTemp, Warning, TEXT("No actors selected"));
        
        if (StatusTextWidget.IsValid())
        {
            StatusTextWidget->SetText(FText::FromString(
                TEXT("ERROR: No actors selected!\n\nPlease select actors in the level before exporting.")
            ));
        }
        return FReply::Handled();
    }
    
    UE_LOG(LogTemp, Warning, TEXT("Exporting %d selected actor(s)"), SelectedActors->Num());
    
    // STEP 2: Get file dialog system
    IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
    if (!DesktopPlatform)
    {
        UE_LOG(LogTemp, Error, TEXT("Could not get desktop platform module"));
        return FReply::Handled();
    }
    
    // STEP 3: Get parent window for dialog
    void* ParentWindowHandle = nullptr;
    IMainFrameModule& MainFrame = FModuleManager::LoadModuleChecked<IMainFrameModule>("MainFrame");
    TSharedPtr<SWindow> MainWindow = MainFrame.GetParentWindow();
    if (MainWindow.IsValid() && MainWindow->GetNativeWindow().IsValid())
    {
        ParentWindowHandle = MainWindow->GetNativeWindow()->GetOSWindowHandle();
    }
    
    // STEP 4: Show SAVE dialog (not open dialog)
    TArray<FString> OutFiles;
    const FString DialogTitle = TEXT("Export USD to Maya");
    const FString DefaultPath = TEXT("C:/SharedUSD/unreal_exports");  // Where Unreal exports TO
    const FString DefaultFile = TEXT("unreal_layout.usda");  // Default filename
    const FString FileTypes = TEXT("USD ASCII (*.usda)|*.usda");  // Only USDA for readability
    const uint32 Flags = 0;
    
    bool bFileSelected = DesktopPlatform->SaveFileDialog(
        ParentWindowHandle,
        DialogTitle,
        DefaultPath,
        DefaultFile,
        FileTypes,
        Flags,
        OutFiles
    );
    
    // STEP 5: Process result
    if (bFileSelected && OutFiles.Num() > 0)
    {
        FString SelectedFile = OutFiles[0];
        UE_LOG(LogTemp, Warning, TEXT("Exporting to: %s"), *SelectedFile);
        
        // Update status
        if (StatusTextWidget.IsValid())
        {
            FString StatusMessage = FString::Printf(
                TEXT("Exporting %d actor(s) to:\n%s\n\nPlease wait..."),
                SelectedActors->Num(),
                *FPaths::GetCleanFilename(SelectedFile)
            );
            StatusTextWidget->SetText(FText::FromString(StatusMessage));
        }
        
        // Actually export the file
        ExportUSDFile(SelectedFile);
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("User cancelled export"));
    }
    
    return FReply::Handled();
}

void FLayoutLinkModule::ExportUSDFile(const FString& FilePath)
{
    UE_LOG(LogTemp, Warning, TEXT("=== Calling Python Export Script ==="));
    UE_LOG(LogTemp, Warning, TEXT("Target: %s"), *FilePath);
    
    // STEP 1: Get the plugin's directory dynamically
    TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("LayoutLink"));
    if (!Plugin.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("Could not find LayoutLink plugin"));
        return;
    }
    
    // Build path to Python script
    FString PluginDir = Plugin->GetBaseDir();
    FString PythonScriptPath = FPaths::Combine(PluginDir, TEXT("Content/Python"));
    
    UE_LOG(LogTemp, Warning, TEXT("Python script path: %s"), *PythonScriptPath);
    
    // STEP 2: Build Python command
    FString AssetLibraryPath = TEXT("C:/SharedUSD/assets");  // ← NEW
    
    FString PythonScript = FString::Printf(
        TEXT("import sys; "
             "sys.path.append(r'%s'); "
             "import layout_export; "
             "result = layout_export.export_selected_to_usd(r'%s', r'%s'); "
             "print('Export result:', result)"),
        *PythonScriptPath,
        *FilePath,
        *AssetLibraryPath
    );
    
    // STEP 3: Execute Python
    FPythonCommandEx PythonCommand;
    PythonCommand.Command = PythonScript;
    PythonCommand.ExecutionMode = EPythonCommandExecutionMode::ExecuteStatement;
    
    bool bSuccess = IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonCommand.Command);
    
    if (bSuccess)
    {
        UE_LOG(LogTemp, Warning, TEXT("Python export completed"));
        
        if (StatusTextWidget.IsValid())
        {
            StatusTextWidget->SetText(FText::FromString(
                TEXT("Export Successful!\n\nPython script created USD file.\nCheck Output Log for details.")
            ));
        }
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Python export failed - check Output Log"));
        
        if (StatusTextWidget.IsValid())
        {
            StatusTextWidget->SetText(FText::FromString(
                TEXT("ERROR: Python export failed!\n\nCheck Output Log for Python errors.")
            ));
        }
    }
}

// ============================================================================
// METADATA READING
// ============================================================================

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
        TEXT("import sys; "
             "sys.path.append(r'%s'); "
             "from pxr import Sdf; "
             "import metadata_utils; "
             "layer = Sdf.Layer.FindOrOpen(r'%s'); "
             "metadata = metadata_utils.read_layoutlink_metadata(layer) if layer else None; "
             "result = metadata_utils.format_metadata_string(metadata); "
             "print('METADATA_RESULT:', result)"),
        *PythonScriptPath,
        *FilePath
    );
    
    // Execute and capture output
    IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonScript);
    
    // For now, return a simple message
    // TODO: Capture Python print output for full metadata display
    return TEXT("Metadata read via Python (check Output Log)");
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FLayoutLinkModule, LayoutLink)