// LayoutLink.cpp
// Main implementation file for the LayoutLink plugin
// Handles USD import from Maya and (soon) export to Maya

#include "LayoutLink.h"

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

// USD includes - MUST be wrapped with Start/End macros to disable Unreal warnings
#include "USDIncludesStart.h"
    #include "pxr/usd/usd/stage.h"
    #include "pxr/usd/sdf/layer.h"
    #include "pxr/usd/usdGeom/xform.h"
    #include "pxr/usd/usdGeom/tokens.h"
    #include "pxr/usd/sdf/path.h"
#include "USDIncludesEnd.h"

// Unreal selection and export
#include "Selection.h"
#include "USDConversionUtils.h"
#include "USDLayerUtils.h"

// Unreal's USD integration
#include "USDStageActor.h"

// File dialog system
#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"

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
    // Imports a USD file from Maya into the Unreal level
    // Creates a USD Stage Actor and loads the file into it
    
    UE_LOG(LogTemp, Warning, TEXT("=== Starting USD Import ==="));
    UE_LOG(LogTemp, Warning, TEXT("File: %s"), *FilePath);
    
    // STEP 1: Verify file exists on disk
    if (!FPaths::FileExists(FilePath))
    {
        UE_LOG(LogTemp, Error, TEXT("File does not exist: %s"), *FilePath);
        
        if (StatusTextWidget.IsValid())
        {
            StatusTextWidget->SetText(FText::FromString(TEXT("ERROR: File not found!")));
        }
        return;
    }
    
#if !WITH_EDITOR
    UE_LOG(LogTemp, Error, TEXT("USD import only works in the Editor."));
    return;
#endif
    
    // STEP 2: Get the currently open level
    // Everything in Unreal exists in a "World" (like Maya's scene)
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
    {
        UE_LOG(LogTemp, Error, TEXT("No world found!"));
        return;
    }
    
    // STEP 3: Read metadata from the USD file before importing
    // This shows who exported it from Maya and when
    FString MetadataInfo = ReadMetadataFromUSD(FilePath);
    UE_LOG(LogTemp, Warning, TEXT("Metadata: %s"), *MetadataInfo);
    
    // STEP 4: Create a USD Stage Actor in the level
    // USD Stage Actor is Unreal's object that displays USD files (like Maya's proxy shape)
    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName("MayaLayoutImport");  // Name it meaningfully
    
    AUsdStageActor* StageActor = World->SpawnActor<AUsdStageActor>(
        AUsdStageActor::StaticClass(),
        FVector::ZeroVector,    // Spawn at origin (0, 0, 0)
        FRotator::ZeroRotator,  // No rotation
        SpawnParams
    );
    
    // STEP 5: Check if spawn succeeded
    if (!StageActor)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to spawn USD Stage Actor"));
        
        if (StatusTextWidget.IsValid())
        {
            StatusTextWidget->SetText(FText::FromString(TEXT("ERROR: Failed to create USD Stage Actor")));
        }
        return;
    }
    
    UE_LOG(LogTemp, Warning, TEXT("Created USD Stage Actor: %s"), *StageActor->GetName());
    
    // STEP 6: Load the USD file into the Stage Actor
    // This actually loads and displays the geometry
    StageActor->SetRootLayer(*FilePath);
    
    // STEP 7: Set animation to frame 0
    StageActor->SetTime(0.0f);
    
    // STEP 8: Update UI with success message
    if (StatusTextWidget.IsValid())
    {
        FString SuccessMessage = FString::Printf(
            TEXT("Import Successful!\n\nFile: %s\n\n%s\n\nUSD Stage Actor created in World Outliner"),
            *FPaths::GetCleanFilename(FilePath),
            *MetadataInfo
        );
        StatusTextWidget->SetText(FText::FromString(SuccessMessage));
    }
    
    UE_LOG(LogTemp, Warning, TEXT("=== USD Import Complete ==="));
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
    UE_LOG(LogTemp, Warning, TEXT("=== Export Placeholder ==="));
    
    // Get selected actors count
    USelection* Selection = GEditor->GetSelectedActors();
    int ActorCount = Selection ? Selection->Num() : 0;
    
    // Create a simple text file as placeholder
    FString FileContent = FString::Printf(
        TEXT("# LayoutLink Export Placeholder\n")
        TEXT("# Selected Actors: %d\n")
        TEXT("# Timestamp: %s\n")
        TEXT("# Artist: %s\n")
        TEXT("# From: Unreal Engine\n")
        TEXT("\n")
        TEXT("# TODO: Geometry export requires Unreal's USD exporter API\n")
        TEXT("# which is currently in beta and has C++ integration issues.\n"),
        ActorCount,
        *FDateTime::UtcNow().ToString(),
        *FPlatformProcess::UserName()
    );
    
    // Write to file
    FFileHelper::SaveStringToFile(FileContent, *FilePath);
    
    UE_LOG(LogTemp, Warning, TEXT("Created placeholder file"));
    
    if (StatusTextWidget.IsValid())
    {
        StatusTextWidget->SetText(FText::FromString(
            TEXT("Placeholder file created.\n\nNote: Full USD geometry export from Unreal\nrequires additional development due to\nUnreal 5.6 USD API limitations.")
        ));
    }
}

// ============================================================================
// METADATA READING
// ============================================================================

FString FLayoutLinkModule::ReadMetadataFromUSD(const FString& FilePath)
{
    // Reads the metadata that Maya added to the USD file
    // Returns a formatted string with artist, timestamp, etc.
    
    UE_LOG(LogTemp, Warning, TEXT("Reading metadata from: %s"), *FilePath);
    
    // STEP 1: Convert Unreal's FString to std::string for USD API
    // USD uses standard C++ strings, Unreal uses FString
    std::string FilePathStd = TCHAR_TO_UTF8(*FilePath);
    
    // STEP 2: Open just the USD layer (not the whole scene)
    // This is fast - only reads metadata, not geometry
    pxr::SdfLayerRefPtr Layer = pxr::SdfLayer::FindOrOpen(FilePathStd);
    
    if (!Layer)
    {
        UE_LOG(LogTemp, Warning, TEXT("Could not open USD layer for metadata"));
        return TEXT("No metadata found");
    }
    
    // STEP 3: Get the customLayerData dictionary
    // This is where Maya stored the metadata using our MetadataManager
    pxr::VtDictionary CustomData = Layer->GetCustomLayerData();
    
    if (CustomData.empty())
    {
        UE_LOG(LogTemp, Warning, TEXT("No custom layer data found"));
        return TEXT("No LayoutLink metadata");
    }
    
    // STEP 4: Create helper function to extract string values
    // Lambda function - like a mini-function defined inline
    auto GetStringValue = [&CustomData](const std::string& Key) -> FString
    {
        // Check if the key exists in the dictionary
        if (CustomData.count(Key) > 0)
        {
            // Get the value
            pxr::VtValue Value = CustomData[Key];
            
            // Check if it's a string type
            if (Value.IsHolding<std::string>())
            {
                // Extract and convert to FString
                std::string StrValue = Value.Get<std::string>();
                return FString(UTF8_TO_TCHAR(StrValue.c_str()));
            }
        }
        return TEXT("N/A");  // Not found or wrong type
    };
    
    // STEP 5: Extract each metadata field
    // These keys match what Maya's MetadataManager writes
    FString Timestamp = GetStringValue("layoutlink_timestamp");
    FString Artist = GetStringValue("layoutlink_artist");
    FString App = GetStringValue("layoutlink_app");
    FString Operation = GetStringValue("layoutlink_operation");
    FString Version = GetStringValue("layoutlink_version");
    
    // STEP 6: Format into readable string
    FString MetadataString = TEXT("=== Maya Export Info ===\n");
    MetadataString += FString::Printf(TEXT("Artist: %s\n"), *Artist);
    MetadataString += FString::Printf(TEXT("Exported: %s\n"), *Timestamp);
    MetadataString += FString::Printf(TEXT("From: %s\n"), *App);
    MetadataString += FString::Printf(TEXT("Version: %s"), *Version);
    
    UE_LOG(LogTemp, Warning, TEXT("Metadata extracted successfully"));
    
    return MetadataString;
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FLayoutLinkModule, LayoutLink)