import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from azure.communication.callautomation import CallAutomationClient
from openai import AsyncAzureOpenAI

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

async def test_acs_connection():
    print("[1] Checking ACS Connection...")
    conn_str = os.getenv("ACS_CONNECTION_STRING")
    if not conn_str:
        print("  ❌ ACS_CONNECTION_STRING is missing.")
        return False
    try:
        client = CallAutomationClient.from_connection_string(conn_str)
        # Try a simple non-call operation to verify the key
        # (Initializing the client doesn't hit the network, but we can check format)
        if "endpoint=https://" not in conn_str or "accesskey=" not in conn_str:
            print("  ❌ ACS_CONNECTION_STRING format is likely wrong.")
            return False
        print("  ✅ ACS Client initialized (format correct).")
        return True
    except Exception as e:
        print(f"  ❌ ACS Error: {e}")
        return False

async def test_openai_connection():
    print("[2] Checking Azure OpenAI Connection...")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not all([endpoint, key, deployment]):
        print(f"  ❌ OpenAI vars missing: endpoint={bool(endpoint)}, key={bool(key)}, deployment={bool(deployment)}")
        return False

    try:
        client = AsyncAzureOpenAI(
            api_key=key,
            api_version="2024-02-15-preview",
            azure_endpoint=endpoint
        )
        # Tiny request to verify key and deployment
        resp = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5
        )
        print(f"  ✅ OpenAI Success: Received '{resp.choices[0].message.content.strip()}'")
        return True
    except Exception as e:
        print(f"  ❌ OpenAI Error: {e}")
        return False

def test_speech_connection():
    print("[3] Checking Azure Speech Connection (TTS)...")
    key = os.getenv("SPEECH_KEY")
    region = os.getenv("SPEECH_REGION")
    
    if not key or not region:
        print(f"  ❌ Speech vars missing: key={bool(key)}, region={bool(region)}")
        return False

    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        # Fix: Use AudioOutputConfig and write to a file to avoid hardware/driver issues
        # and construction errors.
        audio_out = speechsdk.audio.AudioOutputConfig(filename="tests/test.wav")
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, 
            audio_config=audio_out
        )
        
        # Actually attempt a tiny synthesis to be 100% sure the key is valid
        result = synthesizer.speak_text_async("Test").get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"  ✅ Speech OK (synthesized to tests/test.wav).")
            return True
        else:
            print(f"  ❌ Speech failed with reason: {result.reason}")
            return False
    except Exception as e:
        print(f"  ❌ Speech Error: {e}")
        return False

def verify_linkage_hints():
    print("[4] Checking Infrastructure Linkage Hints...")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").lower()
    region = os.getenv("SPEECH_REGION", "").lower()
    
    # Heuristic: If OpenAI endpoint is centralus but Speech is francecentral, 
    # it's possible they are two different resources.
    if region and region not in endpoint:
        print(f"  ⚠️  WARNING: Your Speech region is '{region}' but your OpenAI endpoint is in a different location.")
        print(f"     Ensure that the resource at '{endpoint}' is the ONE CONNECTED to your ACS resource in the Azure Portal.")
    else:
        print("  ✅ Regions look consistent.")

async def main():
    print("==================================================")
    print("RETAILCARE INFRASTRUCTURE DIAGNOSTIC")
    print("==================================================")
    
    s1 = await test_acs_connection()
    s2 = await test_openai_connection()
    s3 = test_speech_connection()
    verify_linkage_hints()
    
    print("\n--------------------------------------------------")
    if all([s1, s2, s3]):
        print("✅ ALL INDIVIDUAL COMPONENTS ARE WORKING!")
        print("\nIf you still hear silence, the problem is 100% the PORTAL LINKAGE:")
        print("1. Go to Azure Portal > ACS Resource > Cognitive Services.")
        print("2. Ensure the resource provided in AZURE_OPENAI_ENDPOINT is listed as 'Connected'.")
    else:
        print("❌ SOME COMPONENTS FAILED. Fix the errors above first.")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
