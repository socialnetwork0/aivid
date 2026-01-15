# Detecting AI-generated video: technical implementation guide

**YouTube and TikTok now expose AI-generated content through specific API fields and standardized metadata formats that can be extracted programmatically.** The key disclosure field on YouTube is `status.containsSyntheticMedia`, while TikTok uses `video_tag` with AIGC type indicators. Both platforms have adopted the C2PA Content Credentials standard, which embeds provenance data in MP4 files via UUID boxes containing JUMBF-formatted manifests. For a Python library like aivid, the most reliable detection approach combines platform API queries, C2PA manifest extraction using `c2pa-python`, and XMP metadata parsing for the `Iptc4xmpExt:DigitalSourceType` field.

## Platform API fields for programmatic detection

**YouTube Data API v3** introduced the `containsSyntheticMedia` boolean field on October 30, 2024, located within the video resource's status object. Query it via:

```
GET https://www.googleapis.com/youtube/v3/videos?part=status&id={VIDEO_ID}
```

The response structure returns:
```json
{
  "status": {
    "containsSyntheticMedia": true,
    "uploadStatus": "processed",
    "privacyStatus": "public"
  }
}
```

This field can also be set during upload via `videos.insert` or updated via `videos.update`. YouTube automatically applies this label when detecting C2PA Content Credentials (version 2.1+) indicating AI generation, or when its internal detection systems flag synthetic content.

**TikTok's Research API** exposes AI disclosure through the `video_tag` struct in query responses:

```
POST https://open.tiktokapis.com/v2/research/video/query/?fields=id,video_tag
```

The response differentiates between creator-labeled and auto-detected AI content:

| video_tag.number | video_tag.type | Meaning |
|------------------|----------------|---------|
| **1** | AIGC Type | Creator labeled as AI-generated |
| **2** | AIGC Type | Platform auto-detected AI content |

TikTok's Research API requires the `research.data.basic` scope and is restricted to approved academic and research applications. The unofficial `TikTokApi` Python package provides broader access but uses browser automation and doesn't expose the `video_tag` field.

## C2PA manifest structure and extraction

C2PA (Coalition for Content Provenance and Authenticity) version **2.2** is the current standard for embedding AI provenance metadata. In MP4 files, C2PA data resides in a **UUID box** with identifier `D8FEC3D6-1B0E-483C-9297-58286EED8DBE`, positioned after the `ftyp` box and before `moov`.

The critical field for AI detection is `digitalSourceType` within the `c2pa.actions` assertion:

```json
{
  "assertion_store": {
    "c2pa.actions": {
      "actions": [{
        "action": "c2pa.created",
        "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
        "softwareAgent": {"name": "GPT-4o"}
      }]
    }
  }
}
```

**IPTC Digital Source Type URIs** that indicate AI generation:

| URI Fragment | Meaning |
|-------------|---------|
| `trainedAlgorithmicMedia` | Fully AI-generated (DALL-E, Sora, Midjourney) |
| `compositeWithTrainedAlgorithmicMedia` | Human content edited with generative AI |
| `compositeSynthetic` | Mix of captured and synthetic elements |
| `algorithmicMedia` | Non-AI algorithmic content (procedural) |

The `c2pa-python` library (v0.27.1, Apache 2.0/MIT license) provides the cleanest extraction interface:

```python
from c2pa import Reader
import json

def extract_c2pa_ai_indicators(video_path):
    try:
        reader = Reader(video_path)
        manifest = json.loads(reader.json())
        
        for manifest_id, data in manifest.get("manifests", {}).items():
            actions = data.get("assertion_store", {}).get("c2pa.actions", {})
            for action in actions.get("actions", []):
                source_type = action.get("digitalSourceType", "")
                if "trainedAlgorithmicMedia" in source_type:
                    return {
                        "ai_generated": True,
                        "source_type": source_type,
                        "generator": action.get("softwareAgent", {}).get("name"),
                        "claim_generator": data.get("claim", {}).get("claim_generator")
                    }
    except Exception:
        pass
    return {"ai_generated": False}
```

## XMP metadata provides a secondary detection layer

When C2PA manifests are stripped or unavailable, the XMP `DigitalSourceType` field offers fallback detection. Located in the IPTC Extension namespace `http://iptc.org/std/Iptc4xmpExt/2008-02-29/`, this field uses the same IPTC vocabulary as C2PA.

**ExifTool extraction:**
```bash
exiftool -XMP-iptcExt:DigitalSourceType video.mp4
```

**Python extraction** via `python-xmp-toolkit`:
```python
from libxmp import XMPFiles

def check_xmp_ai_source(video_path):
    xmp_file = XMPFiles(file_path=video_path)
    xmp = xmp_file.get_xmp()
    if xmp:
        source_type = xmp.get_property(
            "http://iptc.org/std/Iptc4xmpExt/2008-02-29/",
            "DigitalSourceType"
        )
        return "trainedAlgorithmicMedia" in str(source_type)
    return False
```

For comprehensive video metadata including custom boxes, `pymediainfo` (v7.0.1) wraps MediaInfo and returns all track-level data as structured dictionaries.

## SynthID watermarking has limited programmatic access

Google DeepMind's SynthID embeds invisible watermarks using **co-trained neural networks**—one for embedding, one for detection—that modify pixel values imperceptibly. For video, each frame receives the same image watermarking treatment. SynthID survives standard cropping, JPEG compression, color adjustments, and format conversion, with degraded detection only under aggressive compression below ~50% quality.

**Critical limitation:** SynthID detection for images, video, and audio is **not publicly available** as a Python library. Detection requires:
- **SynthID Detector Portal**: Restricted to approved journalists and researchers
- **Vertex AI**: Built-in detection for Imagen/Veo outputs only
- **Gemini App**: Manual upload verification

Only **SynthID Text** is open-source, integrated into Hugging Face Transformers v4.46.0+:

```python
from transformers import SynthIDTextWatermarkingConfig, AutoModelForCausalLM

config = SynthIDTextWatermarkingConfig(
    keys=[1234, 5678, 9012],  # Unique integers
    ngram_len=5
)
# Detection uses BayesianDetectorModel (requires trained checkpoint)
```

## Meta's open-source watermarking fills the detection gap

Meta's **Seal framework** offers MIT-licensed alternatives for watermark detection that aivid can integrate directly:

**AudioSeal** for AI-generated audio:
```python
from audioseal import AudioSeal

detector = AudioSeal.load_detector("audioseal_detector_16bits")
result, message = detector.detect_watermark(audio_tensor, sample_rate)
# result: float [0,1] probability
# message: 16-bit identifier (65,536 possible sources)
```

**Video Seal** (github.com/facebookresearch/videoseal) uses temporal watermark propagation rather than per-frame embedding, providing efficient detection that survives H.264, HEVC, and AV1 encoding.

## Detection strategy for a comprehensive Python library

A robust aivid implementation should layer detection methods by reliability:

1. **Platform API queries** (highest confidence for labeled content)
   - YouTube: `status.containsSyntheticMedia` via Data API v3
   - TikTok: `video_tag.type == "AIGC Type"` via Research API

2. **C2PA manifest extraction** (cryptographically verified provenance)
   - Check `digitalSourceType` for `trainedAlgorithmicMedia`
   - Parse `softwareAgent` for specific AI tool identification
   - Use `c2pa-python` for cross-platform support

3. **XMP metadata fallback** (when C2PA stripped)
   - Read `Iptc4xmpExt:DigitalSourceType` via ExifTool or python-xmp-toolkit

4. **Watermark detection** (for unlabeled content)
   - AudioSeal for audio tracks
   - Video Seal for visual frames
   - Note: SynthID detection unavailable outside Google ecosystem

5. **Heuristic detection** (lowest confidence, academic implementations only)
   - deepfake-o-meter framework integrates XceptionNet, MesoNet, CNNDetection
   - Requires trained models and offers research-grade accuracy (~70-85% F1)

## Recommended dependencies for aivid

| Purpose | Package | Version | License |
|---------|---------|---------|---------|
| C2PA manifests | `c2pa-python` | ≥0.27.1 | Apache 2.0/MIT |
| Video metadata | `pymediainfo` | ≥7.0.1 | MIT |
| XMP extraction | `python-xmp-toolkit` | latest | BSD |
| Audio watermarks | `audioseal` | latest | MIT |
| YouTube API | `python-youtube` | latest | MIT |
| FFprobe wrapper | `ffmpeg-python` | latest | Apache 2.0 |

## Conclusion

The AI content detection landscape has matured significantly—TikTok became the first major video platform to implement C2PA Content Credentials in January 2025, and YouTube's `containsSyntheticMedia` field provides official API-level disclosure. **The most reliable programmatic approach combines platform-specific API fields with C2PA manifest parsing**, as these represent explicit disclosure by creators or platforms rather than probabilistic detection.

For watermark-based detection, Meta's open-source Seal framework provides production-ready tools, while Google's SynthID remains ecosystem-locked. The IPTC `trainedAlgorithmicMedia` vocabulary has emerged as the de facto standard across C2PA, XMP, and platform implementations, making it the single most important string to detect across all metadata sources. Building aivid around this layered approach—APIs first, then C2PA, then XMP, then watermarks—will maximize detection coverage while maintaining explainability for each positive identification.