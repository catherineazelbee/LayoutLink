# animation_sequence_reader.py
# Read animation data from Unreal Level Sequences
# FIXED for Unreal Engine 5.6 API

import unreal


def find_level_sequence_for_actor(actor):
    """
    Find all Level Sequences that contain the given actor.
    
    Args:
        actor: Unreal actor to search for
        
    Returns:
        List of (level_sequence, binding_id) tuples, or empty list if not found
    """
    results = []
    
    # Get all Level Sequence assets in the project
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    
    # UE 5.6+ API: Use TopLevelAssetPath for class specification
    class_name = unreal.TopLevelAssetPath("/Script/LevelSequence", "LevelSequence")
    
    # Get all Level Sequence assets
    assets = asset_registry.get_assets_by_class(class_name, search_sub_classes=True)
    
    unreal.log(f"  Searching {len(assets)} Level Sequences for actor...")
    
    for asset_data in assets:
        try:
            # Load the level sequence
            asset_path = asset_data.get_asset().get_path_name()
            level_seq = unreal.load_asset(asset_path)
            
            if not level_seq:
                continue
            
            # Check if this sequence contains our actor
            bindings = level_seq.get_bindings()
            
            for binding in bindings:
                try:
                    # Get the display name of this binding
                    binding_name = binding.get_display_name()
                    actor_label = actor.get_actor_label()
                    
                    # Match by name - if the binding name matches the actor label
                    if actor_label == binding_name or binding_name in actor_label or actor_label in binding_name:
                        results.append((level_seq, binding.get_id()))
                        unreal.log(f"  ✓ Found match in sequence: {level_seq.get_name()}")
                        break
                        
                except Exception as e:
                    # Skip bindings that fail
                    continue
                    
        except Exception as e:
            # Skip sequences that fail to load
            continue
    
    return results


def sample_actor_animation_from_sequence(actor, level_sequence, start_frame, end_frame):
    """
    Sample actor animation from a Level Sequence by evaluating it at each frame.
    
    Args:
        actor: Unreal actor
        level_sequence: Level Sequence containing the actor
        start_frame: Start frame
        end_frame: End frame
        
    Returns:
        Dict with translate/rotate/scale samples per frame
    """
    samples = {
        'translate': {},
        'rotate': {},
        'scale': {}
    }
    
    if not level_sequence:
        unreal.log_warning("No Level Sequence provided")
        return samples
    
    # FIXED: Use LevelSequenceEditorBlueprintLibrary instead of subsystem
    # Save the current sequence so we can restore it
    original_sequence = None
    original_time = None
    
    try:
        # Try to get the currently open sequence
        original_sequence = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
        original_time = unreal.LevelSequenceEditorBlueprintLibrary.get_current_time()
    except:
        # If no sequence is open, that's fine
        pass
    
    try:
        # Open our target sequence
        unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(level_sequence)
        
        # Get playback range
        seq_start = level_sequence.get_playback_start()
        seq_end = level_sequence.get_playback_end()
        
        unreal.log(f"  Sampling sequence from frame {start_frame} to {end_frame}")
        unreal.log(f"  Sequence range: {seq_start} to {seq_end}")
        
        # Pause playback to ensure we're evaluating at specific frames
        unreal.LevelSequenceEditorBlueprintLibrary.pause()
        
        # Sample at each frame
        for frame in range(int(start_frame), int(end_frame) + 1):
            # Set the sequencer time to this frame
            unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)
            
            # Small delay to ensure evaluation completes
            import time
            time.sleep(0.001)
            
            # Read the actor's transform at this frame
            xf = actor.get_actor_transform()
            loc = xf.translation
            rot = xf.rotation.rotator()
            scl = xf.scale3d
            
            samples['translate'][frame] = (float(loc.x), float(loc.y), float(loc.z))
            samples['rotate'][frame] = (float(rot.roll), float(rot.pitch), float(rot.yaw))
            samples['scale'][frame] = (float(scl.x), float(scl.y), float(scl.z))
        
        unreal.log(f"  ✓ Sampled {len(samples['translate'])} frames")
        
    except Exception as e:
        unreal.log_error(f"Error sampling animation: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Restore original sequence and time
        if original_sequence:
            try:
                unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(original_sequence)
                if original_time is not None:
                    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(original_time)
            except:
                pass
    
    return samples


def get_actor_animation_from_sequencer(actor, start_frame, end_frame):
    """
    Main function: Get actor's animation data from any Level Sequence that contains it.
    
    This is the REPLACEMENT for the broken sample_actor_animation() function.
    
    Args:
        actor: Unreal actor
        start_frame: Start frame
        end_frame: End frame
        
    Returns:
        Dict with translate/rotate/scale samples per frame, or None if no animation found
    """
    # First, try to find a Level Sequence containing this actor
    sequences = find_level_sequence_for_actor(actor)
    
    if not sequences:
        # No sequence found - actor is not animated in Sequencer
        unreal.log(f"  Actor not found in any Level Sequence - treating as static")
        return None
    
    # Use the first sequence we found
    level_sequence, binding_id = sequences[0]
    
    unreal.log(f"  Found actor in sequence: {level_sequence.get_name()}")
    
    # Sample the animation
    samples = sample_actor_animation_from_sequence(
        actor, 
        level_sequence, 
        start_frame, 
        end_frame
    )
    
    return samples


def has_varying_samples(samples):
    """Check if samples actually vary (not all the same)"""
    if not samples:
        return False
    
    # Check translate
    t_values = list(samples['translate'].values())
    if len(set(t_values)) > 1:
        return True
    
    # Check rotate
    r_values = list(samples['rotate'].values())
    if len(set(r_values)) > 1:
        return True
    
    # Check scale  
    s_values = list(samples['scale'].values())
    if len(set(s_values)) > 1:
        return True
    
    return False