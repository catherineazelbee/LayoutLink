// LayoutLink.Build.cs

using UnrealBuildTool;

public class LayoutLink : ModuleRules
{
	public LayoutLink(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(
			new string[] {
				"Core"
			});

		PrivateDependencyModuleNames.AddRange(
			new string[] {
				"Projects",
				"CoreUObject",
				"Engine",
				"Slate",
				"SlateCore",
				"USDStage",
				"UnrealUSDWrapper",
				"DesktopPlatform"
			});

		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(
				new string[] {
					"UnrealEd",
					"LevelEditor",
					"ToolMenus"
				});
		}
	}
}

