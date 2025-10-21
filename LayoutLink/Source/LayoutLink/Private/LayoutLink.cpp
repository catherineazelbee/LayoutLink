// Copyright Epic Games, Inc. All Rights Reserved.

#include "LayoutLink.h"
#include "LayoutLinkStyle.h"
#include "LayoutLinkCommands.h"
#include "LevelEditor.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "ToolMenus.h"

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

TSharedRef<SDockTab> FLayoutLinkModule::OnSpawnPluginTab(const FSpawnTabArgs &SpawnTabArgs)
{
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		[
			// Main vertical container (stacks widgets top to bottom)
			SNew(SVerticalBox)

			// === HEADER ===
			+ SVerticalBox::Slot()
			.AutoHeight() // only takes space needed
			.Padding(10.0f) // 10 pixel spacing
			[
				(SNewTextBlock)
				.Text(FText::FromString("Import Layout from Maya"))
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 16))
				.Justification(ETextJustify::Center)
			]

			// === IMPORT BUTTOM ===
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
			.FillHeight(1.0f) // Take remaining space
			.Padding(10.0f)
			[
				SNew(SButton)
				.Text(FText::FromString("Click Import to load USD files from Maya \n 
					\n Shared folder: C:/SharedUSD/unreal_exports"))
				.AutoWrapText(true)
			]


			SNew(SBox)
			.HAlign(HAlign_Center)
			.VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text(WidgetText)
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

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FLayoutLinkModule, LayoutLink)