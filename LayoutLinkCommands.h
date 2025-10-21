// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "Framework/Commands/Commands.h"
#include "LayoutLinkStyle.h"

class FLayoutLinkCommands : public TCommands<FLayoutLinkCommands>
{
public:

	FLayoutLinkCommands()
		: TCommands<FLayoutLinkCommands>(TEXT("LayoutLink"), NSLOCTEXT("Contexts", "LayoutLink", "LayoutLink Plugin"), NAME_None, FLayoutLinkStyle::GetStyleSetName())
	{
	}

	// TCommands<> interface
	virtual void RegisterCommands() override;

public:
	TSharedPtr< FUICommandInfo > OpenPluginWindow;
};