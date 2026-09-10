#!/usr/bin/env python3
"""Check Groq quota status and estimate reset time."""

import sys
import os
from datetime import datetime, timezone, timedelta

print("=" * 80)
print("GROQ QUOTA ANALYSIS")
print("=" * 80)

# Get current UTC time
now_utc = datetime.now(timezone.utc)
print(f"\n📍 Current UTC time: {now_utc.isoformat()}")
print(f"   (Local offset from UTC: use your system clock to convert to your timezone)")

print("\n" + "=" * 80)
print("QUOTA RESET MECHANISM")
print("=" * 80)

print("""
Groq's daily token quotas (TPD - Tokens Per Day) typically work as follows:

✓ Confirmed behaviors from your error messages:
  1. Quota is PER MODEL per organization
  2. Max tokens requested (not just generated) are counted against quota
  3. Currently for qwen/qwen3.6-27b: 200,000 TPD limit

⏰ Most likely reset mechanics:
  
  Option A: Midnight UTC reset (most common for APIs)
    - Resets at 00:00 UTC every day
    - Next reset: 2026-08-25 00:00:00 UTC
    - Estimated wait: depends on current UTC time
    - Time until reset: calculated below
    
  Option B: Rolling 24-hour window
    - Resets 24h from first request of the day
    - Need to know when first request was made today
    - Less common but possible

⚠️  What we know from your error messages:
    - Last error showed: "Please try again in 5m48s"
    - This suggests: Groq knows exactly when quota resets
    - And: Quota resets on a fixed schedule (not rolling)
    - Conclusion: Likely midnight UTC reset

""")

print("=" * 80)
print("TIME CALCULATION")
print("=" * 80)

# Calculate time until midnight UTC
tomorrow_midnight_utc = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
time_until_reset = tomorrow_midnight_utc - now_utc

hours = int(time_until_reset.total_seconds() // 3600)
minutes = int((time_until_reset.total_seconds() % 3600) // 60)
seconds = int(time_until_reset.total_seconds() % 60)

print(f"\n🕐 Assuming midnight UTC reset (00:00 UTC):")
print(f"   Next quota reset: 2026-08-25 00:00:00 UTC")
print(f"   Time remaining: {hours}h {minutes}m {seconds}s")
print(f"\n   ⏰ Come back in: ~{hours} hours")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

if hours > 2:
    print(f"""
✓ RECOMMENDATION: WAIT for quota reset

  Reason: You have {hours}+ hours to wait. It's more practical to wait than to 
  debug quota issues or find workarounds.
  
  Action plan:
    1. Wait until 2026-08-25 00:00:00 UTC (midnight)
    2. At that time, Groq quota resets to 200,000 tokens
    3. Resume testing with single context_precision call (max_tokens=1800)
    
  Cost analysis for next session (after reset):
    - Single context_precision call: ~1,800 tokens
    - Single context_recall call: ~1,800 tokens  
    - Dry-run backfill (4 execs × 2 metrics): ~14,400 tokens
    - Existing metrics (faithfulness/answer_relevancy): ~4 × 4 × 1,200 = ~19,200 tokens
    - Total estimate: ~37,400 tokens out of 200,000 available
    - Safe margin: Yes, comfortably under budget
""")
else:
    print(f"""
✗ URGENT: Quota resets very soon

  Remaining time: {hours}h {minutes}m {seconds}s
  
  At that exact moment, your 200,000 token quota resets.
  Be ready to test immediately after.
""")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)

print(f"""
1. ✓ Note the reset time: 2026-08-25 00:00:00 UTC
2. ✓ Wait until that time (check your system clock against UTC)
3. ✓ After reset, I will make ONE test call: context_precision on exec 4
4. ✓ Show you the full raw response + token usage
5. ✓ Only then proceed to context_recall test
6. ✓ Then (if both pass) run dry-run backfill for 4 executions

Status: ⏳ WAITING FOR QUOTA RESET
""")
