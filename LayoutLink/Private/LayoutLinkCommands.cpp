// Copyright Epic Games, Inc. All Rights Reserved.

#include "LayoutLinkCommands.h"

#define LOCTEXT_NAMESPACE "FLayoutLinkModule"

void FLayoutLinkCommands::RegisterCommands()
{
	UI_COMMAND(OpenPluginWindow, "LayoutLink", "Bring up LayoutLink window", EUserInterfaceActionType::Button, FInputChord());
}

#undef LOCTEXT_NAMESPACE
