"""Default output formatter - concise AI video analysis."""

import re

from aivid.models import VideoMetadata


def format_default(metadata: VideoMetadata) -> str:
    """Format metadata as concise default output.

    Focuses on AI video analysis with:
    - AI generation info (generator, created time, title)
    - Video specs (duration, resolution, fps, size)
    - C2PA validation status
    """
    lines = []
    filename = metadata.filename

    lines.append("=" * 70)
    lines.append(f"File: {filename}")
    lines.append("=" * 70)

    # Source section (if video was downloaded from URL)
    source = metadata.source
    if source.is_from_url:
        lines.append("")
        lines.append("## SOURCE")
        lines.append(f"  Platform:     {source.platform.value.capitalize()}")
        if source.original_url:
            lines.append(f"  URL:          {source.original_url}")
        if source.video_id:
            lines.append(f"  Video ID:     {source.video_id}")
        if source.uploader:
            lines.append(f"  Uploader:     {source.uploader}")
        if source.title:
            lines.append(f"  Title:        {source.title}")

    # AI Generation section (if C2PA or AI detected)
    c2pa = metadata.provenance.c2pa
    ai = metadata.ai_detection
    desc = metadata.descriptive
    platform_aigc = metadata.provenance.platform_aigc

    if c2pa.has_c2pa or ai.is_ai_generated:
        lines.append("")
        lines.append("## AI GENERATION")

        # Generator
        generator = ai.generator or c2pa.claim_generator or "Unknown"
        lines.append(f"  Generator:    {generator}")

        # Creation time - prefer creation_timestamp with source attribution
        creation_ts = desc.creation_timestamp
        if creation_ts.value:
            time_str = creation_ts.value.strftime("%Y-%m-%d %H:%M:%S UTC")
            source = creation_ts.source or "unknown"
            lines.append(f"  Created:      {time_str} (source: {source})")
        elif c2pa.signature_time:
            # Fallback to signature_time
            time_str = c2pa.signature_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            lines.append(f"  Created:      {time_str} (source: c2pa signature)")

        # Title
        if c2pa.title:
            lines.append(f"  Title:        {c2pa.title}")

            # Task ID (Internal ID) - prefer model field, fallback to regex extraction
            if c2pa.task_id:
                lines.append(f"  Task ID:      {c2pa.task_id}")
            else:
                # Fallback: extract UUID from title like "e9eb1f95b29946bbbbcb0f2eba129c17_media.mp4"
                match = re.match(r"([a-f0-9]{32})_", c2pa.title)
                if match:
                    lines.append(f"  Task ID:      {match.group(1)}")

        # Instance ID (XMP unique identifier)
        if c2pa.instance_id:
            lines.append(f"  Instance ID:  {c2pa.instance_id}")

        # Digital source type
        if c2pa.digital_source_type:
            lines.append(f"  Source Type:  {c2pa.digital_source_type}")

        # Generation mode - prefer model field, fallback to inference [ANALYSIS]
        if c2pa.generation_mode:
            lines.append(f"  Gen Mode:     {c2pa.generation_mode} [ANALYSIS]")
        elif c2pa.has_c2pa:
            gen_mode = "image/video-to-video" if c2pa.ingredient_count > 0 else "text-to-video"
            lines.append(f"  Gen Mode:     {gen_mode} [ANALYSIS]")

        # Signer info
        if c2pa.issuer and c2pa.signer_name:
            lines.append(f"  Signed By:    {c2pa.issuer} ({c2pa.signer_name})")
        elif c2pa.issuer:
            lines.append(f"  Signed By:    {c2pa.issuer}")

        # Actions
        if c2pa.actions:
            action_names = [a.action for a in c2pa.actions]
            lines.append(f"  Actions:      {', '.join(action_names)}")

        # Ingredients (important: distinguishes text-to-video vs image/video-to-video)
        if c2pa.ingredient_count > 0:
            lines.append(f"  Ingredients:  {c2pa.ingredient_count} item(s)")
        else:
            lines.append("  Ingredients:  None")

    # Platform AIGC section (TikTok embedded metadata)
    if platform_aigc.has_tiktok_metadata:
        lines.append("")
        lines.append("## PLATFORM AIGC (TikTok)")

        # AIGC label type
        if platform_aigc.tiktok_aigc_label_type is not None:
            label_desc = "AI Generated" if platform_aigc.tiktok_aigc_label_type == 2 else "Unknown"
            lines.append(f"  AIGC Label:   {platform_aigc.tiktok_aigc_label_type} ({label_desc})")
        else:
            lines.append("  AIGC Label:   None (Human Content)")

        # Video ID
        if platform_aigc.tiktok_video_id:
            lines.append(f"  Video ID:     {platform_aigc.tiktok_video_id}")

        # Video MD5
        if platform_aigc.tiktok_video_md5:
            lines.append(f"  Video MD5:    {platform_aigc.tiktok_video_md5}")

    # YouTube API section (from YouTube Data API v3)
    if platform_aigc.youtube_contains_synthetic_media is not None:
        lines.append("")
        lines.append("## YOUTUBE API")
        if platform_aigc.youtube_video_id:
            lines.append(f"  Video ID:     {platform_aigc.youtube_video_id}")
        if platform_aigc.youtube_contains_synthetic_media:
            lines.append("  AI Label:     Yes - Contains Synthetic Media")
        else:
            lines.append("  AI Label:     No AI label detected")

    # Watermark Detection section
    watermarks = metadata.provenance.watermarks
    if watermarks.detections:
        lines.append("")
        lines.append("## WATERMARK DETECTION")
        for detection in watermarks.detections:
            icon = "Yes" if detection.detected else "No"
            conf_str = f" ({detection.confidence:.1%})" if detection.detected else ""
            lines.append(f"  {detection.detector.capitalize()}:    {icon}{conf_str}")
        if watermarks.has_watermark:
            lines.append("  Summary:      Watermark detected")

    # Video Info section
    lines.append("")
    lines.append("## VIDEO INFO")

    tech = metadata.technical

    # Duration
    lines.append(f"  Duration:     {tech.duration_formatted}")

    # Resolution with aspect ratio
    video = tech.video
    if video.width and video.height:
        aspect = video.aspect_ratio
        if aspect:
            lines.append(f"  Resolution:   {video.width}x{video.height} ({aspect})")
        else:
            lines.append(f"  Resolution:   {video.width}x{video.height}")

    # Frame rate
    if video.fps:
        lines.append(f"  Frame Rate:   {video.fps:.0f} fps")

    # Size
    lines.append(f"  Size:         {metadata.file_info.size_human}")

    # Bitrate
    if tech.bitrate:
        mbps = tech.bitrate / 1_000_000
        lines.append(f"  Bitrate:      {mbps:.1f} Mbps")

    # Audio (important: 96kHz is Sora signature, others use 48kHz)
    audio = tech.audio
    if audio.sample_rate:
        khz = audio.sample_rate / 1000
        channel_info = ""
        if audio.channel_layout:
            channel_info = audio.channel_layout
        elif audio.channels:
            channel_info = f"{audio.channels}ch"
        lines.append(f"  Audio:        {khz:.0f}kHz {channel_info}".rstrip())

    # C2PA Validation section (if C2PA detected)
    if c2pa.has_c2pa:
        lines.append("")
        lines.append("## C2PA VALIDATION")
        lines.append(f"  Status:       {c2pa.validation_state or 'Unknown'}")

        # Trust status
        if c2pa.cert_trusted is not None:
            trust_icon = "✓" if c2pa.cert_trusted else "✗"
            trust_text = (
                "Certificate chain verified" if c2pa.cert_trusted else "Certificate NOT trusted"
            )
            lines.append(f"  Trusted:      {trust_icon} {trust_text}")

        if c2pa.manifest_id:
            lines.append(f"  Manifest ID:  {c2pa.manifest_id}")

        # SDK version
        if c2pa.claim_generator_version:
            sdk_str = c2pa.claim_generator_product or "c2pa"
            lines.append(f"  SDK:          {sdk_str} {c2pa.claim_generator_version}")

        # Signature algorithm
        if c2pa.signature_algorithm:
            alg = c2pa.signature_algorithm.upper()  # Normalize to uppercase
            # Map common algorithm names
            alg_names = {
                "ES256": "ECDSA P-256",
                "ES384": "ECDSA P-384",
                "ES512": "ECDSA P-521",
                "PS256": "RSA-PSS SHA-256",
                "PS384": "RSA-PSS SHA-384",
                "PS512": "RSA-PSS SHA-512",
            }
            alg_desc = alg_names.get(alg, "")
            if alg_desc:
                lines.append(f"  Signature:    {alg} ({alg_desc})")
            else:
                lines.append(f"  Signature:    {alg}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)
