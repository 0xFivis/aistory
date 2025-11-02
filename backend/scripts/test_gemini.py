"""
Test script for Google Gemini service

Usage:
    python scripts/test_gemini.py
"""
import sys
import os
from pathlib import Path

# Add backend/src to path
backend_src = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(backend_src))

from app.services.gemini_service import GeminiService
from app.services.exceptions import ServiceException
import json


def test_storyboard_generation():
    """Test basic storyboard generation"""
    
    print("=" * 60)
    print("Testing Google Gemini Storyboard Generation")
    print("=" * 60)
    
    # Test content
    video_content = """
    唐朝诗人李白，号称"诗仙"，以其豪放不羁的性格和浪漫主义诗风闻名于世。
    他一生游历名山大川，创作了大量脍炙人口的诗篇，如《将进酒》、《静夜思》等。
    他的诗歌充满了对自由的向往和对自然的热爱。
    """
    
    try:
        # Initialize service
        print("\n1. Initializing Gemini service...")
        service = GeminiService()
        print("✓ Service initialized successfully")
        
        # Generate storyboard
        print("\n2. Generating storyboard (5 scenes)...")
        scenes = service.generate_storyboard(
            video_content=video_content,
            num_scenes=5,
            language="中文"
        )
        
        print(f"✓ Generated {len(scenes)} scenes")
        
        # Display results
        print("\n3. Storyboard Results:")
        print("-" * 60)
        for scene in scenes:
            print(f"\n场景 {scene['scene_number']}:")
            print(f"  旁白: {scene['narration']}")
            print(f"  字数: {scene['narration_word_count']}")
            print(f"  图片提示词: {scene['image_prompt'][:100]}...")
        
        # Save to file
        output_file = Path(__file__).parent.parent / "test_output_storyboard.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 60)
        print(f"✓ Results saved to: {output_file}")
        print("✓ Test completed successfully!")
        print("=" * 60)
        
        return True
        
    except ServiceException as e:
        if getattr(e, 'code', '') == "CONFIG_ERROR" or 'Configuration error' in getattr(e, 'message', ''):
            print("\n⚠️  Skipping API call test: Missing API key configuration for Gemini.")
            return True
        print(f"\n✗ Service error: {e.message}")
        print(f"  Code: {e.code}")
        if e.details:
            print(f"  Details: {e.details}")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_validation():
    """Test input validation"""
    
    print("\n" + "=" * 60)
    print("Testing Input Validation")
    print("=" * 60)
    
    service = GeminiService()
    
    # Test empty content
    print("\n1. Testing empty content...")
    try:
        service.generate_storyboard(video_content="", num_scenes=5)
        print("✗ Should have raised ValidationException")
        return False
    except ServiceException as e:
        print(f"✓ Correctly raised: {e.code}")
    
    # Test invalid scene count
    print("\n2. Testing invalid scene count...")
    try:
        service.generate_storyboard(video_content="test", num_scenes=999)
        print("✗ Should have raised ValidationException")
        return False
    except ServiceException as e:
        print(f"✓ Correctly raised: {e.code}")
    
    print("\n✓ Validation tests passed!")
    return True


if __name__ == "__main__":
    print("\n🚀 Starting Gemini Service Tests\n")
    
    # Run tests
    validation_passed = test_validation()
    storyboard_passed = test_storyboard_generation()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Validation Tests: {'✓ PASSED' if validation_passed else '✗ FAILED'}")
    print(f"  Storyboard Generation: {'✓ PASSED' if storyboard_passed else '✗ FAILED'}")
    print("=" * 60)
    
    sys.exit(0 if (validation_passed and storyboard_passed) else 1)
