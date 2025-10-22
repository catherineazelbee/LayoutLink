// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "Modules/ModuleManager.h"

class FToolBarBuilder;
class FMenuBuilder;

class FLayoutLinkModule : public IModuleInterface
{
public:
	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	/** This function will be bound to Command (by default it will bring up plugin window) */
	void PluginButtonClicked();

private:
	void RegisterMenus();

	TSharedRef<class SDockTab> OnSpawnPluginTab(const class FSpawnTabArgs &SpawnTabArgs);

	// NEW FUNCTIONS
	FReply OnImportButtonClicked();						  // handles button click, open file dialogue
	void ImportUSDFile(const FString &FilePath);		  // actually imports USD file
	FString ReadMetadataFromUSD(const FString &FilePath); // reads Maya metadata

private:
	TSharedPtr<class FUICommandList> PluginCommands;

	// NEW VARIABLE
	TSharedPtr<class STextBlock> StatusTextWidget; // stored reference to status text
};
