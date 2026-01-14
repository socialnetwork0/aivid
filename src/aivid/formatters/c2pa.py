"""C2PA focused output formatter - AI detection report."""

from aivid.models import VideoMetadata


def format_c2pa(metadata: VideoMetadata) -> str:
    """Format metadata as C2PA/AI detection focused output.

    Focuses on:
    - C2PA Content Credentials detection
    - AI generation indicators
    - Detection confidence levels
    """
    lines = []
    filename = metadata.filename

    lines.append("=" * 70)
    lines.append("C2PA / AI CONTENT DETECTION REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Quick summary
    lines.append(f"File: {filename}")
    lines.append(f"Size: {metadata.file_info.size_human}")
    lines.append("")

    # C2PA Detection Result
    c2pa = metadata.provenance.c2pa
    if c2pa.has_c2pa:
        lines.append("[+] C2PA METADATA DETECTED")
        lines.append("-" * 40)
        lines.append(f"  Source: {c2pa.source}")
        lines.append(f"  Manifest ID: {c2pa.manifest_id}")
        if c2pa.title:
            lines.append(f"  Title: {c2pa.title}")
        if c2pa.claim_generator:
            lines.append(f"  Claim Generator: {c2pa.claim_generator}")
        if c2pa.issuer:
            lines.append(f"  Issuer: {c2pa.issuer}")
        if c2pa.signer_name:
            lines.append(f"  Signer: {c2pa.signer_name}")
        if c2pa.signature_time:
            lines.append(f"  Signed: {c2pa.signature_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if c2pa.digital_source_type:
            lines.append(f"  Digital Source Type: {c2pa.digital_source_type}")
        if c2pa.validation_state:
            lines.append(f"  Validation: {c2pa.validation_state}")
    else:
        lines.append("[-] NO C2PA METADATA FOUND")

    lines.append("")

    # AI Generation Indicators
    lines.append("## AI GENERATION INDICATORS")
    lines.append("-" * 40)

    ai = metadata.ai_detection
    tech = metadata.technical

    # Show audio sample rate
    if tech.audio.sample_rate:
        rate = tech.audio.sample_rate
        indicator = " [SORA SIGNATURE]" if rate == 96000 else ""
        lines.append(f"  Audio sample rate: {rate} Hz{indicator}")

    # Show encoder
    if tech.video.encoder:
        lines.append(f"  Encoder: {tech.video.encoder}")

    # Show handler
    if tech.video.handler:
        lines.append(f"  Handler: {tech.video.handler}")

    # Format tags encoder
    format_encoder = metadata.raw.format_tags.get("encoder")
    if format_encoder:
        lines.append(f"  Format encoder: {format_encoder}")

    lines.append("")

    # Detection Signals
    lines.append("## DETECTION SIGNALS")
    lines.append("-" * 40)

    if ai.signals:
        for _name, signal in ai.signals.items():
            confidence = f"{signal.confidence * 100:.0f}%"
            icon = "✓" if signal.detected else "✗"
            lines.append(f"  {icon} [{confidence:>4}] {signal.name}")
            if signal.description:
                lines.append(f"           {signal.description}")
    else:
        lines.append("  No AI detection signals found")
        lines.append("  (This does NOT mean the video is not AI-generated)")

    lines.append("")

    # Detection Summary
    lines.append("## DETECTION SUMMARY")
    lines.append("-" * 40)

    if ai.is_ai_generated:
        lines.append("  ✓ AI-GENERATED CONTENT DETECTED")
        if ai.generator:
            lines.append(f"    Generator: {ai.generator}")
        lines.append(f"    Confidence: {ai.confidence * 100:.0f}%")
    else:
        lines.append("  No conclusive AI generation evidence found")

    lines.append("")

    # Video Info for context
    lines.append("## VIDEO INFO")
    lines.append("-" * 40)
    video = tech.video
    if video.width and video.height:
        lines.append(f"  Resolution: {video.width}x{video.height}")
    if video.fps:
        lines.append(f"  Frame rate: {video.fps:.0f} fps")
    if tech.duration:
        lines.append(f"  Duration: {tech.duration_formatted}")
    if video.codec:
        profile = f" ({video.profile})" if video.profile else ""
        lines.append(f"  Codec: {video.codec}{profile}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)
