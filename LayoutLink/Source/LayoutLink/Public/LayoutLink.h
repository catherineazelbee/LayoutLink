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
	void ExportUSDFile(const FString &FilePath);
	void ImportUSDFile(const FString &FilePath);
	FString ReadMetadataFromUSD(const FString &FilePath);

	// User-editable settings
	FString AssetLibraryPath;   // e.g. C:/SharedUSD/assets/unreal
	FString LayoutExportDir;    // e.g. C:/SharedUSD/layouts/unreal_layouts

	// UI callbacks for the settings controls
	FReply OnBrowseAssetLibrary();
	FReply OnBrowseLayoutExport();
	void   LoadSettings();
	void   SaveSettings();

private:
	TSharedPtr<class FUICommandList> PluginCommands;
	TSharedPtr<class STextBlock> StatusTextWidget;
};