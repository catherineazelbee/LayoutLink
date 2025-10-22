// Copyright Epic Games, Inc. All Rights Reserved.

#include "LayoutLink.h"
#include "LayoutLinkCommands.h"
#include "LayoutLinkStyle.h"
#include "LevelEditor.h"
#include "ToolMenus.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

// USD includes - must be wrapped with special macros
#include "USDIncludesEnd.h"
#include "USDIncludesStart.h"
#include "pxr/usd/sdf/layer.h"
#include "pxr/usd/usd/stage.h"

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

void FLayoutLinkModule::StartupModule() {
  // This code will execute after your module is loaded into memory; the exact
  // timing is specified in the .uplugin file per-module

  FLayoutLinkStyle::Initialize();
  FLayoutLinkStyle::ReloadTextures();

  FLayoutLinkCommands::Register();

  PluginCommands = MakeShareable(new FUICommandList);

  PluginCommands->MapAction(
      FLayoutLinkCommands::Get().OpenPluginWindow,
      FExecuteAction::CreateRaw(this, &FLayoutLinkModule::PluginButtonClicked),
      FCanExecuteAction());

  UToolMenus::RegisterStartupCallback(
      FSimpleMulticastDelegate::FDelegate::CreateRaw(
          this, &FLayoutLinkModule::RegisterMenus));

  FGlobalTabmanager::Get()
      ->RegisterNomadTabSpawner(
          LayoutLinkTabName,
          FOnSpawnTab::CreateRaw(this, &FLayoutLinkModule::OnSpawnPluginTab))
      .SetDisplayName(LOCTEXT("FLayoutLinkTabTitle", "LayoutLink"))
      .SetMenuType(ETabSpawnerMenuType::Hidden);
}

void FLayoutLinkModule::ShutdownModule() {
  // This function may be called during shutdown to clean up your module.  For
  // modules that support dynamic reloading, we call this function before
  // unloading the module.

  UToolMenus::UnRegisterStartupCallback(this);

  UToolMenus::UnregisterOwner(this);

  FLayoutLinkStyle::Shutdown();

  FLayoutLinkCommands::Unregister();

  FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(LayoutLinkTabName);
}

TSharedRef<SDockTab>
FLayoutLinkModule::OnSpawnPluginTab(const FSpawnTabArgs &SpawnTabArgs) {
  return SNew(SDockTab).TabRole(ETabRole::NomadTab)[
      // Main vertical container (stacks widgets top to bottom)
      SNew(SVerticalBox)

      // === HEADER ===
      + SVerticalBox::Slot().AutoHeight().Padding(
            10.0f)[SNew(STextBlock)
                       .Text(FText::FromString("Import Layout from Maya"))
                       .Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))
                       .Justification(ETextJustify::Center)]

      // === BIG IMPORT BUTTON ===
      + SVerticalBox::Slot().AutoHeight().Padding(
            10.0f)[SNew(SButton)
                       .Text(FText::FromString("IMPORT USD FROM MAYA"))
                       .OnClicked_Raw(
                           this, &FLayoutLinkModule::OnImportButtonClicked)]

      // === STATUS TEXT ===
      +
      SVerticalBox::Slot().FillHeight(1.0f).Padding(10.0f)
          [SNew(SScrollBox) // allows scrolling if text too long
           + SScrollBox::Slot()[
                 // Save reference to this widget so we can update it
                 SAssignNew(StatusTextWidget,
                            STextBlock) // SAssign stores it in StatusTextWidget
                     .Text(FText::FromString(
                         "Click Import to load USD files from Maya \n\nShared "
                         "Folder: C:/SharedUSD/unreal_exports"))
                     .AutoWrapText(true)]]];
}

void FLayoutLinkModule::PluginButtonClicked() {
  FGlobalTabmanager::Get()->TryInvokeTab(LayoutLinkTabName);
}

void FLayoutLinkModule::RegisterMenus() {
  // Owner will be used for cleanup in call to UToolMenus::UnregisterOwner
  FToolMenuOwnerScoped OwnerScoped(this);

  {
    UToolMenu *Menu =
        UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
    {
      FToolMenuSection &Section = Menu->FindOrAddSection("WindowLayout");
      Section.AddMenuEntryWithCommandList(
          FLayoutLinkCommands::Get().OpenPluginWindow, PluginCommands);
    }
  }

  {
    UToolMenu *ToolbarMenu = UToolMenus::Get()->ExtendMenu(
        "LevelEditor.LevelEditorToolBar.PlayToolBar");
    {
      FToolMenuSection &Section = ToolbarMenu->FindOrAddSection("PluginTools");
      {
        FToolMenuEntry &Entry =
            Section.AddEntry(FToolMenuEntry::InitToolBarButton(
                FLayoutLinkCommands::Get().OpenPluginWindow));
        Entry.SetCommandList(PluginCommands);
      }
    }
  }
}
FReply FLayoutLinkModule::OnImportButtonClicked() {
  UE_LOG(LogTemp, Warning, TEXT("=== Opening File Dialogue ==="));

  // STEP 1: Get the desktop platform module for file dialogues
  // Provides cross-platform file browsing
  IDesktopPlatform *DesktopPlatform = FDesktopPlatformModule::Get();
  if (!DesktopPlatform) {
    UE_LOG(LogTemp, Warning, TEXT("Could not get desktop platform module"));
    return FReply::Handled();
  }

  // STEP 2: Get the main Unreal window to use as parent for dialog
  const void *ParentWindowHandle =
      FSlateApplication::Get().FindBestParentWindowHandleForDialogue(nullptr);

  // STEP 3: Setup file dialog parameters
  TArray<FString> OutFiles; // Array to store selected file paths
  const FString DialogTitle = TEXT("Import USD from Maya");
  const FString DefaultPath =
      TEXT("C:/SharedUSD/unreal_exports"); // start directory
  const FString DefaultFile = TEXT("");    // no default file
  const FString FileTypes = TEXT(
      "USD Files (*.usd;*.usda,*.usdc)|*.usd,*usda,*usdc"); // start directory
  const uint32 Flags = 0; // dialog flags (0=default)

  // STEP 4: Show the file dialog (opens Windows file browser)
  bool bFileSelected = DesktopPlatform->OpenFileDialog(
      ParentWindowHandle, DialogTitle, DefaultPath, DefaultFile, FileTypes,
      Flags,
      OutFiles // selected files go here
  );

  // STEP 5: Check if user selected a file (or cancelled)
  if (bFileSelected && OutFiles.Num() > 0) {
    // user selected a file
    FString SelectedFile = OutFiles[0];
    UE_LOG(LogTemp, Warning, TEXT("User selected file %s"), *SelectedFile);

    // update status text
    if (StatusTextWidget.IsValid()) {
      FString StatusMessage =
          FString::Printf(TEXT("Importing: %s\n\nPlease wait..."),
                          *FPaths::GetCleanFilename(SelectedFile));
      StatusTextWidget->SetText(FText::FromString(StatusMessage));
    }

    // STEP 6: Import the selected USD file
    ImportUSDFile(SelectedFile);
  } else {
    // user cancelled message
    UE_LOG(LogTemp, Warning, TEXT("User cancelled file selection"));
  }

  return FReply::Handled();
}

void FLayoutLinkModule::ImportUSDFile(const FString &FilePath) {
  UE_LOG(LogTemp, Warning, TEXT("=== Starting USD Import"));
  UE_LOG(LogTemp, Warning, TEXT("File: %s"), *FilePath);

  // STEP 1: Verify the file exists
  if (!FPaths::FileExists(FilePath)) {
    UE_LOG(LogTemp, Error, TEXT("File does not exist: %s"), *FilePath);

    if (StatusTextWidget.IsValid()) {
      StatusTextWidget->SetText(
          FText::FromString(TEXT("ERROR: File not found")));
    }
    return;
  }

  // STEP 2: Get the current world (the user's open level)
  UWorld *World = GEditor->GetEditorWorldContext().World();
  if (!World) {
    UE_LOG(LogTemp, Error, TEXT("No world found!"));
    return;
  }

  // STEP 3: Read metadata from the USD file before importing
  FString MetadataInfo = ReadMetadataFromUSD(FilePath);
  UE_LOG(LogTemp, Warning, TEXT("Metadata: %s"), *MetadataInfo);

  // STEP 4: Create a USD Stage Actor in the level
  FActorSpawnParameters SpawnParams;
  SpawnParams.Name = FName("MayaLayoutImport"); // name of stage actor

  // spawn the actor at world origin
  AUsdStageActor *StageActor = World->SpawnActor<AUsdStageActor>(
      AUsdStageActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroVector,
      SpawnParams);

  // STEP 5: Check if spawn succeeded
  if (!StageActor) {
    UE_LOG(LogTemp, Error, TEXT("Failed to spawn USD Stage Actor"));

    if (StatusTextWidget.IsValid()) {
      StatusTextWidget->SetText(
          FText::FromString(TEXT("ERROR: Failed to create USD Stage Actor")));
    }
    return;
  }

  UE_LOG(LogTemp, Warning, TEXT("Created USD Stage Actor: %s"),
         *StageActor->GetName());

  // STEP 6: Load the USD file into the Stage Actor
  StageActor->SetRootLayer(*FilePath);

  // STEP 7: Set the time code to start of animation(0.0f)
  StageActor->SetTime(0.0f);

  // STEP 8: Update the status text with success message
  if (StatusTextWidget.IsValid()) {
    FString SuccessMessage =
        FString::Printf(TEXT("✓ Import Successful!\n\nFile: %s\n\n%s\n\nUSD "
                             "Stage Actor created in World Outliner"),
                        *FPaths::GetCleanFilename(FilePath), *MetadataInfo);
    StatusTextWidget->SetText(FText::FromString(SuccessMessage));

    UE_LOG(LogTemp, Warning, TEXT("=== USD Import Complete ==="));
  }
}

FString FLayoutLinkModule::ReadMetadataFromUSD(const FString &FilePath) {
  UE_LOG(LogTemp, Warning, TEXT("Reading metadata from: %s"), *FilePath);

  // STEP 1: Convert Unreal FString to std::string for USD API
  std::string FilePathStd = TCHAR_TO_UTF8(*FilePath);

  // STEP 2: Open the USD layer
  pxr::SdfLayerRefPtr Layer = pxr::SdfLayer::FindOrOpen(FilePathStd);

  if (!Layer) {
    UE_LOG(LogTemp, Warning, TEXT("Could not open USD layer for metadata"));
    return TEXT("No metadata found");
  }

  // STEP 3: Get the customLayerData
  pxr::VtDictionary CustomData = Layer->GetCustomLayerData();

  if (CustomData.empty()) {
    UE_LOG(LogTemp, Warning, TEXT("No custom layer data found"));
    return TEXT("No LayoutLink metadata");
  }

  // STEP 4: Extract metadata keys
  FString MetadataString = TEXT("=== Maya Export Info ===\n");

  // Helper lambda - FIXED SYNTAX
  auto GetStringValue = [&CustomData](const std::string &Key) -> FString {
    if (CustomData.count(Key) > 0) {
      pxr::VtValue Value = CustomData[Key];

      if (Value.IsHolding<std::string>()) {
        std::string StrValue = Value.Get<std::string>();
        return FString(UTF8_TO_TCHAR(StrValue.c_str()));
      }
    }
    return TEXT("N/A");
  };

  // STEP 5: Extract each metadata field
  FString Timestamp = GetStringValue("layoutlink_timestamp");
  FString Artist = GetStringValue("layoutlink_artist");
  FString App = GetStringValue("layoutlink_app");
  FString Operation = GetStringValue("layoutlink_operation");
  FString Version = GetStringValue("layoutlink_version");

  // STEP 6: Build readable string
  MetadataString += FString::Printf(TEXT("Artist: %s\n"), *Artist);
  MetadataString += FString::Printf(TEXT("Exported: %s\n"), *Timestamp);
  MetadataString += FString::Printf(TEXT("From: %s\n"), *App);
  MetadataString += FString::Printf(TEXT("Version: %s"), *Version);

  UE_LOG(LogTemp, Warning, TEXT("Metadata extracted successfully"));

  return MetadataString;
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FLayoutLinkModule, LayoutLink)