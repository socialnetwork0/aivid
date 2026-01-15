"""Full output formatter - comprehensive metadata dump."""

from typing import Any

from aivid.models import VideoMetadata


def _format_dict(d: dict[str, Any], indent: int = 2) -> list[str]:
    """Format a dictionary as indented lines."""
    lines = []
    prefix = " " * indent
    for key, value in d.items():
        if value is None or value == "" or value == [] or value == {}:
            continue
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_format_dict(value, indent + 2))
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                lines.append(f"{prefix}{key}: [{len(value)} items]")
            else:
                lines.append(f"{prefix}{key}: {value}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return lines


def format_full(metadata: VideoMetadata) -> str:
    """Format metadata as comprehensive full output.

    Includes all available metadata from all extractors.
    """
    lines = []

    lines.append("=" * 70)
    lines.append("MEDIA METADATA REPORT (FULL)")
    lines.append("=" * 70)
    lines.append("")

    # File Info
    lines.append("## FILE INFORMATION")
    fi = metadata.file_info
    lines.append(f"  filename: {fi.filename}")
    lines.append(f"  path: {fi.path}")
    lines.append(f"  size_bytes: {fi.size_bytes}")
    lines.append(f"  size_human: {fi.size_human}")
    if fi.created:
        lines.append(f"  created: {fi.created.isoformat()}")
    if fi.modified:
        lines.append(f"  modified: {fi.modified.isoformat()}")
    if fi.accessed:
        lines.append(f"  accessed: {fi.accessed.isoformat()}")
    lines.append(f"  extension: {fi.extension}")
    lines.append("")

    # Source Info (if downloaded from URL)
    source = metadata.source
    if source.is_from_url:
        lines.append("## SOURCE INFORMATION")
        lines.append(f"  platform: {source.platform.value}")
        if source.original_url:
            lines.append(f"  original_url: {source.original_url}")
        if source.video_id:
            lines.append(f"  video_id: {source.video_id}")
        if source.downloaded_path:
            lines.append(f"  downloaded_path: {source.downloaded_path}")
        if source.download_timestamp:
            lines.append(f"  download_timestamp: {source.download_timestamp.isoformat()}")
        if source.uploader:
            lines.append(f"  uploader: {source.uploader}")
        if source.uploader_id:
            lines.append(f"  uploader_id: {source.uploader_id}")
        if source.upload_date:
            lines.append(f"  upload_date: {source.upload_date.isoformat()}")
        if source.title:
            lines.append(f"  title: {source.title}")
        if source.description:
            # Truncate long descriptions
            desc_preview = source.description[:200]
            if len(source.description) > 200:
                desc_preview += "..."
            lines.append(f"  description: {desc_preview}")
        if source.duration_seconds:
            lines.append(f"  duration_seconds: {source.duration_seconds}")
        if source.view_count:
            lines.append(f"  view_count: {source.view_count:,}")
        if source.like_count:
            lines.append(f"  like_count: {source.like_count:,}")
        if source.comment_count:
            lines.append(f"  comment_count: {source.comment_count:,}")
        if source.tags:
            lines.append(f"  tags: {', '.join(source.tags[:10])}")
            if len(source.tags) > 10:
                lines.append(f"    ... and {len(source.tags) - 10} more tags")
        if source.categories:
            lines.append(f"  categories: {', '.join(source.categories)}")
        lines.append("")

    # Technical Info
    tech = metadata.technical
    lines.append("## TECHNICAL INFORMATION")
    if tech.container:
        lines.append(f"  container: {tech.container}")
    if tech.container_long:
        lines.append(f"  container_long: {tech.container_long}")
    if tech.duration:
        lines.append(f"  duration: {tech.duration:.6f}s")
    if tech.bitrate:
        lines.append(f"  bitrate: {tech.bitrate}")
    if tech.nb_streams:
        lines.append(f"  nb_streams: {tech.nb_streams}")
    lines.append("")

    # Video Stream
    video = tech.video
    if video.codec:
        lines.append("  [VIDEO]")
        lines.append(f"    codec: {video.codec}")
        if video.codec_long:
            lines.append(f"    codec_long: {video.codec_long}")
        if video.profile:
            lines.append(f"    profile: {video.profile}")
        if video.width and video.height:
            lines.append(f"    resolution: {video.width}x{video.height}")
        if video.fps:
            lines.append(f"    fps: {video.fps}")
        if video.bitrate:
            lines.append(f"    bitrate: {video.bitrate}")
        if video.pixel_format:
            lines.append(f"    pixel_format: {video.pixel_format}")
        if video.encoder:
            lines.append(f"    encoder: {video.encoder}")
        if video.handler:
            lines.append(f"    handler: {video.handler}")
        lines.append("")

    # Audio Stream
    audio = tech.audio
    if audio.codec:
        lines.append("  [AUDIO]")
        lines.append(f"    codec: {audio.codec}")
        if audio.codec_long:
            lines.append(f"    codec_long: {audio.codec_long}")
        if audio.profile:
            lines.append(f"    profile: {audio.profile}")
        if audio.sample_rate:
            lines.append(f"    sample_rate: {audio.sample_rate}")
            # Note unusual sample rates that may indicate AI generation
            if audio.sample_rate == 96000:
                lines.append("    sample_rate_note: Sora signature (typical: 48000)")
            elif audio.sample_rate not in (44100, 48000, 22050, 11025, 8000, 16000):
                lines.append("    sample_rate_note: Unusual rate (typical: 44100/48000)")
        if audio.channels:
            lines.append(f"    channels: {audio.channels}")
        if audio.channel_layout:
            lines.append(f"    channel_layout: {audio.channel_layout}")
        if audio.bitrate:
            lines.append(f"    bitrate: {audio.bitrate}")
        lines.append("")

    # C2PA / Provenance
    c2pa = metadata.provenance.c2pa
    if c2pa.has_c2pa:
        lines.append("## C2PA / PROVENANCE")
        lines.append(f"  has_c2pa: {c2pa.has_c2pa}")
        lines.append(f"  source: {c2pa.source}")
        if c2pa.manifest_id:
            lines.append(f"  manifest_id: {c2pa.manifest_id}")
        if c2pa.title:
            lines.append(f"  title: {c2pa.title}")
        if c2pa.task_id:
            lines.append(f"  task_id: {c2pa.task_id}")
        if c2pa.instance_id:
            lines.append(f"  instance_id: {c2pa.instance_id}")
        if c2pa.claim_generator:
            lines.append(f"  claim_generator: {c2pa.claim_generator}")
        if c2pa.software_agent:
            lines.append(f"  software_agent: {c2pa.software_agent}")
        if c2pa.claim_generator_version:
            lines.append(f"  c2pa_sdk_version: {c2pa.claim_generator_version}")
        if c2pa.issuer:
            lines.append(f"  issuer: {c2pa.issuer}")
        if c2pa.signer_name:
            lines.append(f"  signer_name: {c2pa.signer_name}")
        if c2pa.signature_time:
            lines.append(f"  signature_time: {c2pa.signature_time.isoformat()}")
        if c2pa.signature_algorithm:
            lines.append(f"  signature_algorithm: {c2pa.signature_algorithm}")
        if c2pa.digital_source_type:
            lines.append(f"  digital_source_type: {c2pa.digital_source_type}")
        if c2pa.validation_state:
            lines.append(f"  validation_state: {c2pa.validation_state}")
        # cert_trusted: show explicitly even if False
        if c2pa.cert_trusted is not None:
            lines.append(f"  cert_trusted: {c2pa.cert_trusted}")
        if c2pa.actions:
            lines.append(f"  actions: {len(c2pa.actions)} action(s)")
            for action in c2pa.actions:
                action_info = f"    - {action.action}"
                if action.when:
                    action_info += f" (when: {action.when.isoformat()})"
                lines.append(action_info)
        # Ingredients: show explicitly even if None
        if c2pa.ingredient_count > 0:
            lines.append(f"  ingredients: {c2pa.ingredient_count} ingredient(s)")
            for ing in c2pa.ingredients[:5]:  # Limit to first 5
                ing_title = ing.get("title", "unknown")
                ing_format = ing.get("format", "")
                lines.append(f"    - {ing_title} ({ing_format})")
            if c2pa.ingredient_count > 5:
                lines.append(f"    ... and {c2pa.ingredient_count - 5} more")
        else:
            lines.append("  ingredients: None")
        if c2pa.generation_mode:
            lines.append(f"  generation_mode: {c2pa.generation_mode} [ANALYSIS]")
        lines.append("")

        # Validation details subsection
        has_validation_details = any(
            [
                c2pa.timestamp_validated is not None,
                c2pa.timestamp_responder,
                c2pa.claim_signature_valid is not None,
                c2pa.cert_chain,
                c2pa.validation_errors,
            ]
        )
        if has_validation_details:
            lines.append("  [VALIDATION DETAILS]")
            if c2pa.timestamp_validated is not None:
                lines.append(f"    timestamp_validated: {c2pa.timestamp_validated}")
            if c2pa.timestamp_responder:
                lines.append(f"    timestamp_responder: {c2pa.timestamp_responder}")
            if c2pa.claim_signature_valid is not None:
                lines.append(f"    claim_signature_valid: {c2pa.claim_signature_valid}")
            if c2pa.cert_chain:
                lines.append(f"    cert_chain: {c2pa.cert_chain}")
            if c2pa.validation_errors:
                lines.append("    warnings:")
                for err in c2pa.validation_errors:
                    if err:
                        lines.append(f"      - {err}")
            lines.append("")

    # AI Detection
    ai = metadata.ai_detection
    if ai.is_ai_generated or ai.signals:
        lines.append("## AI DETECTION")
        lines.append(f"  is_ai_generated: {ai.is_ai_generated}")
        if ai.generator:
            lines.append(f"  generator: {ai.generator}")
        if ai.generator_raw:
            lines.append(f"  generator_raw: {ai.generator_raw}")
        # Show inferred model for generators with multiple models (e.g., Sora)
        if ai.inferred_model or ai.model_confidence:
            if ai.inferred_model:
                lines.append(
                    f"  inferred_model: {ai.inferred_model} ({ai.model_confidence}) [ANALYSIS]"
                )
            else:
                # No model could be inferred
                res = metadata.technical.video.resolution or "unknown"
                if ai.model_confidence == "ambiguous":
                    lines.append(f"  inferred_model: sora-2 or sora-2-pro ({res}) [ANALYSIS]")
                else:
                    lines.append(f"  inferred_model: unknown ({res}) [ANALYSIS]")
        lines.append(f"  confidence: {ai.confidence:.2f}")
        if ai.signing_authorities:
            lines.append(f"  signing_authorities: {', '.join(ai.signing_authorities)}")
        if ai.signals:
            # Separate facts from analysis
            facts = {k: v for k, v in ai.signals.items() if v.is_fact}
            analysis = {k: v for k, v in ai.signals.items() if not v.is_fact}

            if facts:
                lines.append("  signals [FACT - from metadata]:")
                for name, signal in facts.items():
                    icon = "✓" if signal.detected else "✗"
                    lines.append(f"    {icon} {name}: {signal.description or ''}")
            if analysis:
                lines.append("  signals [ANALYSIS - inferred]:")
                for name, signal in analysis.items():
                    icon = "✓" if signal.detected else "✗"
                    lines.append(f"    {icon} {name}: {signal.description or ''}")
        lines.append("")

    # Platform API Labels (YouTube/TikTok API results)
    platform_aigc = metadata.provenance.platform_aigc
    has_platform_api = any(
        [
            platform_aigc.youtube_contains_synthetic_media is not None,
            platform_aigc.tiktok_api_video_tag_type is not None,
        ]
    )
    if has_platform_api:
        lines.append("## PLATFORM API LABELS")

        # YouTube API
        if platform_aigc.youtube_contains_synthetic_media is not None:
            lines.append("  [YOUTUBE DATA API v3]")
            if platform_aigc.youtube_video_id:
                lines.append(f"    video_id: {platform_aigc.youtube_video_id}")
            lines.append(
                f"    contains_synthetic_media: {platform_aigc.youtube_contains_synthetic_media}"
            )
            if platform_aigc.youtube_contains_synthetic_media:
                lines.append("    interpretation: Video contains AI-generated content")
            else:
                lines.append("    interpretation: No AI label from YouTube")

        # TikTok Research API
        if platform_aigc.tiktok_api_video_tag_type is not None:
            lines.append("  [TIKTOK RESEARCH API]")
            if platform_aigc.tiktok_api_video_tag_number is not None:
                tag_meaning = {
                    1: "Creator labeled",
                    2: "Auto-detected",
                }.get(platform_aigc.tiktok_api_video_tag_number, "Unknown")
                lines.append(
                    f"    video_tag_number: {platform_aigc.tiktok_api_video_tag_number} ({tag_meaning})"
                )
            lines.append(f"    video_tag_type: {platform_aigc.tiktok_api_video_tag_type}")
            if platform_aigc.is_tiktok_api_ai_labeled:
                lines.append("    interpretation: TikTok flagged as AI-generated")

        lines.append("")

    # Watermark Detection
    watermarks = metadata.provenance.watermarks
    if watermarks.detections:
        lines.append("## WATERMARK DETECTION")
        lines.append(f"  has_watermark: {watermarks.has_watermark}")
        lines.append(f"  overall_confidence: {watermarks.overall_confidence:.2f}")
        lines.append(f"  detectors_run: {len(watermarks.detections)}")
        lines.append("")

        for detection in watermarks.detections:
            lines.append(f"  [{detection.detector.upper()}]")
            lines.append(f"    detected: {detection.detected}")
            lines.append(f"    confidence: {detection.confidence:.4f}")
            if detection.watermark_type:
                lines.append(f"    watermark_type: {detection.watermark_type}")
            if detection.message_bits:
                lines.append(f"    message_bits: {detection.message_bits}")
            if detection.message_decoded:
                lines.append(f"    message_decoded: {detection.message_decoded}")
            if detection.frames_analyzed:
                lines.append(f"    frames_analyzed: {detection.frames_analyzed}")
            if detection.positive_frames is not None:
                lines.append(f"    positive_frames: {detection.positive_frames}")
            if detection.detection_threshold is not None:
                lines.append(f"    detection_threshold: {detection.detection_threshold}")

        lines.append("")

    # Descriptive Metadata
    desc = metadata.descriptive
    has_desc = any(
        [
            desc.title,
            desc.creator,
            desc.description,
            desc.software,
            desc.creation_timestamp.value,
        ]
    )
    if has_desc:
        lines.append("## DESCRIPTIVE METADATA")
        if desc.title:
            lines.append(f"  title: {desc.title}")
        if desc.creator:
            lines.append(f"  creator: {desc.creator}")
        if desc.description:
            lines.append(f"  description: {desc.description}")
        if desc.software:
            lines.append(f"  software: {desc.software}")
        if desc.copyright:
            lines.append(f"  copyright: {desc.copyright}")
        lines.append("")

        # Timestamp tracking with source attribution
        lines.append("  [TIMESTAMPS]")
        if desc.creation_timestamp.value:
            ts = desc.creation_timestamp
            lines.append(f"    creation_time: {ts.value.isoformat()}")
            lines.append(f"    creation_source: {ts.source}")
            if ts.raw_value:
                lines.append(f"    creation_raw: {ts.raw_value}")
        if desc.modification_timestamp.value:
            ts = desc.modification_timestamp
            lines.append(f"    modification_time: {ts.value.isoformat()}")
            lines.append(f"    modification_source: {ts.source}")
        lines.append("")

    # IPTC AI Metadata (2025.1)
    iptc_ai = desc.iptc_ai
    has_iptc_ai = any(
        [
            iptc_ai.ai_system_used,
            iptc_ai.ai_generated,
            iptc_ai.ai_prompt_info,
        ]
    )
    if has_iptc_ai:
        lines.append("## IPTC AI METADATA (2025.1)")
        if iptc_ai.ai_generated is not None:
            lines.append(f"  ai_generated: {iptc_ai.ai_generated}")
        if iptc_ai.ai_system_used:
            lines.append(f"  ai_system_used: {iptc_ai.ai_system_used}")
        if iptc_ai.ai_system_version:
            lines.append(f"  ai_system_version: {iptc_ai.ai_system_version}")
        if iptc_ai.ai_prompt_info:
            lines.append(f"  ai_prompt_info: {iptc_ai.ai_prompt_info}")
        if iptc_ai.ai_prompt_writer_name:
            lines.append(f"  ai_prompt_writer_name: {iptc_ai.ai_prompt_writer_name}")
        if iptc_ai.ai_training_mining_usage:
            lines.append(f"  ai_training_mining_usage: {iptc_ai.ai_training_mining_usage}")
        lines.append("")

    # Raw Data
    raw = metadata.raw

    # Box structure
    if raw.box_structure:
        lines.append("## MP4 BOX STRUCTURE")
        for box in raw.box_structure[:50]:
            indent = "  " * box.depth
            lines.append(f"  {indent}{box.type:8s} size={box.size:>12,}  offset={box.offset}")
        if len(raw.box_structure) > 50:
            lines.append(f"  ... and {len(raw.box_structure) - 50} more boxes")
        lines.append("")

    # Format tags
    if raw.format_tags:
        lines.append("## FORMAT TAGS")
        for key, value in raw.format_tags.items():
            lines.append(f"  {key}: {value}")
        lines.append("")

    # Interesting strings
    if raw.strings:
        lines.append("## INTERESTING STRINGS")
        for s in raw.strings[:30]:
            lines.append(f"  {s[:150]}")
        if len(raw.strings) > 30:
            lines.append(f"  ... and {len(raw.strings) - 30} more")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)
