// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class LayoutLink : ModuleRules
{
	public LayoutLink(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicIncludePaths.AddRange(
			new string[] {
				// ... add public include paths required here ...
			}
			);


		PrivateIncludePaths.AddRange(
			new string[] {
				// ... add other private include paths required here ...
			}
			);


		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
				"InputCore",
				"UnrealEd",
				"Slate",
				"SlateCore",
				// added dependencies
				"Json", // reads metadata
				"JsonUtilities", // parses JSON
				"USDImporter", // USD import functionality
				"USDStage", // USD Stage Actor
				"UnrealUSDWrapper", // USD C++ API Wrapper from Pixar
				"DesktopPlatform" // for file dialogs
			}
			);


		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"Projects",
				"InputCore",
				"EditorFramework",
				"UnrealEd",
				"ToolMenus",
				"CoreUObject",
				"Engine",
				"Slate",
				"SlateCore",
				// ... add private dependencies here
			}
			);


		DynamicallyLoadedModuleNames.AddRange(
			new string[]
			{
				// ... add any modules that your module loads dynamically here ...
			}
			);
	}
}
