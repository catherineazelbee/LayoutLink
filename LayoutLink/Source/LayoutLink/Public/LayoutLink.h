// LayoutLink.h

#pragma once

#include "Modules/ModuleManager.h"

class FToolBarBuilder;
class FMenuBuilder;

class FLayoutLinkModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	void PluginButtonClicked();

private:
#if WITH_EDITOR
    void RegisterMenus();
    TSharedRef<class SDockTab> OnSpawnPluginTab(const class FSpawnTabArgs &SpawnTabArgs);
#endif

    FReply OnImportButtonClicked();
    FReply OnExportButtonClicked();
    FReply OnExportMeshLibraryClicked();
    FReply OnBrowseAssetLibrary();
    FReply OnBrowseLayoutExport();
	FReply OnGetFrameRangeFromSequence();
    
    void ExportUSDFile(const FString &FilePath);
    void ImportUSDFile(const FString &FilePath);
    FString ReadMetadataFromUSD(const FString &FilePath);

    void LoadSettings();
    void SaveSettings();

    // User-editable settings
    FString AssetLibraryPath;
    FString LayoutExportDir;
    
    // Frame range settings
    int32 StartFrame = 1;
    int32 EndFrame = 120;

private:
    TSharedPtr<class FUICommandList> PluginCommands;
    TSharedPtr<class STextBlock> StatusTextWidget;
};