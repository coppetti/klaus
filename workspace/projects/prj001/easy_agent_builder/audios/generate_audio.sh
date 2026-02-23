#!/bin/bash
# Generate TED Talk Audio using macOS 'say' command
# =================================================

set -e

echo "🎙️ Easy Agent Builder - Audio Generator"
echo "=========================================="
echo ""

# Configuration
VOICE="Samantha"
RATE="180"  # Words per minute
FORMAT="aiff"

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This script requires macOS 'say' command"
    echo "   For Linux/Windows, consider using:"
    echo "   - Google Cloud Text-to-Speech"
    echo "   - Amazon Polly"
    echo "   - OpenAI TTS API"
    exit 1
fi

# Create output directory
mkdir -p generated

echo "🎤 Configuration:"
echo "   Voice: $VOICE"
echo "   Rate: $RATE wpm"
echo "   Format: $FORMAT"
echo ""

# Function to generate audio
generate_audio() {
    local input_file=$1
    local output_name=$2
    
    echo "📝 Processing: $input_file"
    
    # Count words
    word_count=$(wc -w < "$input_file")
    est_duration=$((word_count * 60 / RATE))
    
    echo "   Words: $word_count"
    echo "   Est. duration: ~${est_duration}s"
    
    # Generate audio
    say -v "$VOICE" -r "$RATE" -f "$input_file" -o "generated/${output_name}.${FORMAT}"
    
    echo "   ✅ Generated: generated/${output_name}.${FORMAT}"
    echo ""
}

# Check for arguments
if [ "$1" == "--all" ]; then
    echo "🎯 Generating ALL audio files..."
    echo ""
    
    # Tech Summary
    generate_audio "TECH_SUMMARY_PART_1_Opening.txt" "tech_summary_part_1"
    generate_audio "TECH_SUMMARY_PART_2_Architecture.txt" "tech_summary_part_2"
    generate_audio "TECH_SUMMARY_PART_3_Integration.txt" "tech_summary_part_3"
    generate_audio "TECH_SUMMARY_PART_4_Testing.txt" "tech_summary_part_4"
    generate_audio "TECH_SUMMARY_PART_5_Conclusion.txt" "tech_summary_part_5"
    
    # Business Summary
    generate_audio "BUSINESS_SUMMARY_PART_1_The_Cost.txt" "business_summary_part_1"
    generate_audio "BUSINESS_SUMMARY_PART_2_ROI.txt" "business_summary_part_2"
    generate_audio "BUSINESS_SUMMARY_PART_3_Risk.txt" "business_summary_part_3"
    generate_audio "BUSINESS_SUMMARY_PART_4_Implementation.txt" "business_summary_part_4"
    generate_audio "BUSINESS_SUMMARY_PART_5_The_Choice.txt" "business_summary_part_5"
    
    echo "🎉 All files generated successfully!"
    
elif [ "$1" == "--tech" ]; then
    echo "🎯 Generating Tech Summary only..."
    echo ""
    
    generate_audio "TECH_SUMMARY_PART_1_Opening.txt" "tech_summary_part_1"
    generate_audio "TECH_SUMMARY_PART_2_Architecture.txt" "tech_summary_part_2"
    generate_audio "TECH_SUMMARY_PART_3_Integration.txt" "tech_summary_part_3"
    generate_audio "TECH_SUMMARY_PART_4_Testing.txt" "tech_summary_part_4"
    generate_audio "TECH_SUMMARY_PART_5_Conclusion.txt" "tech_summary_part_5"
    
    echo "🎉 Tech Summary generated!"
    
elif [ "$1" == "--business" ]; then
    echo "🎯 Generating Business Summary only..."
    echo ""
    
    generate_audio "BUSINESS_SUMMARY_PART_1_The_Cost.txt" "business_summary_part_1"
    generate_audio "BUSINESS_SUMMARY_PART_2_ROI.txt" "business_summary_part_2"
    generate_audio "BUSINESS_SUMMARY_PART_3_Risk.txt" "business_summary_part_3"
    generate_audio "BUSINESS_SUMMARY_PART_4_Implementation.txt" "business_summary_part_4"
    generate_audio "BUSINESS_SUMMARY_PART_5_The_Choice.txt" "business_summary_part_5"
    
    echo "🎉 Business Summary generated!"
    
elif [ "$1" == "--test" ]; then
    echo "🧪 Running test (first 30 seconds of Tech Part 1)..."
    echo ""
    
    # Extract first paragraph for testing
    head -n 10 TECH_SUMMARY_PART_1_Opening.txt > /tmp/test_input.txt
    say -v "$VOICE" -r "$RATE" -f /tmp/test_input.txt -o "generated/test_sample.${FORMAT}"
    
    echo "✅ Test file generated: generated/test_sample.${FORMAT}"
    echo "   Play it with: afplay generated/test_sample.${FORMAT}"
    
else
    echo "Usage:"
    echo "  ./generate_audio.sh --all       # Generate all audio files"
    echo "  ./generate_audio.sh --tech      # Generate Tech Summary only"
    echo "  ./generate_audio.sh --business  # Generate Business Summary only"
    echo "  ./generate_audio.sh --test      # Generate test sample (30s)"
    echo ""
    echo "Options:"
    echo "  Change VOICE variable in script (default: Samantha)"
    echo "  Change RATE variable in script (default: 180 wpm)"
    echo ""
    echo "Available voices:"
    say -v '?' | head -10
    echo "  ... (use 'say -v ?' to see all)"
fi

echo ""
echo "📁 Output directory: generated/"
echo ""
echo "To convert to MP3 (requires ffmpeg):"
echo "  ffmpeg -i input.aiff -codec:a libmp3lame -qscale:a 2 output.mp3"
