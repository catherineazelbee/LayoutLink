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
				"Core","CoreUObject","Engine","Slate","SlateCore","Json","JsonUtilities",
			}
			);


		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
			"Projects","EditorFramework","UnrealEd","ToolMenus","LevelEditor",
            "DesktopPlatform",
            // USD (Editor side)
            "USDImporter","USDStage","UnrealUSDWrapper",
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
