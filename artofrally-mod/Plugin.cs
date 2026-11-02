using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using BepInEx;
using BepInEx.Configuration;
using UnityEngine;

namespace HeadlookArtOfRally
{
    // DefaultExecutionOrder large => our LateUpdate runs AFTER Cinemachine's brain,
    // so we add the head-look offset on top of the game's computed camera pose each frame.
    [BepInPlugin("com.headlook.artofrally", "Headlook FreeLook", "1.0.0")]
    [DefaultExecutionOrder(10000)]
    public class Plugin : BaseUnityPlugin
    {
        const int PORT = 4242;

        UdpClient _udp;
        Thread _rx;
        volatile bool _run = true;
        volatile float _yaw, _pitch, _roll;     // latest absolute head angles (deg) from the tracker
        volatile int _lastRxTick;               // Environment.TickCount of the last good packet
        volatile bool _gotPacket;
        const int STALE_MS = 500;                // no packet for this long (face lost / tracker gone) -> ease to forward

        float _nYaw, _nPitch;                    // neutral (recenter) reference
        bool _haveNeutral;
        bool _enabled = true;

        ConfigEntry<float> _gainYaw, _gainPitch, _maxYaw, _maxPitch, _smooth;
        ConfigEntry<bool> _invertYaw, _invertPitch;
        ConfigEntry<KeyCode> _modifierKey, _recenterKey, _toggleKey;
        float _sYaw, _sPitch;                    // smoothed offsets

        void Awake()
        {
            _gainYaw     = Config.Bind("look", "gainYaw", 2.0f, "head-yaw degrees -> camera-yaw degrees");
            _gainPitch   = Config.Bind("look", "gainPitch", 2.0f, "head-pitch degrees -> camera-pitch degrees");
            _maxYaw      = Config.Bind("look", "maxYaw", 130f, "clamp camera yaw offset (deg)");
            _maxPitch    = Config.Bind("look", "maxPitch", 70f, "clamp camera pitch offset (deg)");
            _smooth      = Config.Bind("look", "smoothing", 0.35f, "0..1, higher = smoother/laggier");
            _invertYaw   = Config.Bind("look", "invertYaw", false, "flip left/right");
            _invertPitch = Config.Bind("look", "invertPitch", true, "flip up/down");
            _modifierKey = Config.Bind("keys", "modifier", KeyCode.LeftShift, "hold this together with the keys below");
            _recenterKey = Config.Bind("keys", "recenter", KeyCode.K, "recenter neutral (hold modifier): Shift+K by default");
            _toggleKey   = Config.Bind("keys", "toggle", KeyCode.L, "toggle head-look (hold modifier): Shift+L by default");

            try
            {
                _udp = new UdpClient(new IPEndPoint(IPAddress.Loopback, PORT));
                _rx = new Thread(RxLoop) { IsBackground = true };
                _rx.Start();
                Logger.LogInfo("Headlook FreeLook loaded — listening udp 127.0.0.1:" + PORT);
            }
            catch (Exception e)
            {
                Logger.LogError("Headlook: UDP bind failed: " + e.Message);
            }
        }

        void RxLoop()
        {
            var ep = new IPEndPoint(IPAddress.Any, 0);
            while (_run)
            {
                try
                {
                    byte[] b = _udp.Receive(ref ep);   // opentrack packet: 6 doubles x,y,z,yaw,pitch,roll
                    if (b.Length >= 48)
                    {
                        float yaw   = (float)BitConverter.ToDouble(b, 24);
                        float pitch = (float)BitConverter.ToDouble(b, 32);
                        float roll  = (float)BitConverter.ToDouble(b, 40);
                        if (float.IsNaN(yaw) || float.IsInfinity(yaw) ||
                            float.IsNaN(pitch) || float.IsInfinity(pitch)) continue;   // a NaN would poison the smoothing forever
                        _yaw = yaw; _pitch = pitch; _roll = roll;
                        _lastRxTick = Environment.TickCount;
                        _gotPacket = true;
                    }
                }
                catch { if (!_run) break; }
            }
        }

        void OnDestroy()
        {
            _run = false;
            try { _udp?.Close(); } catch { }
        }

        void Update()
        {
            bool mod = Input.GetKey(_modifierKey.Value);
            if (mod && Input.GetKeyDown(_toggleKey.Value))
            {
                _enabled = !_enabled;
                Logger.LogInfo("Headlook " + (_enabled ? "ON" : "OFF"));
            }
            if (mod && Input.GetKeyDown(_recenterKey.Value) && _gotPacket)
            {
                _nYaw = _yaw; _nPitch = _pitch; _haveNeutral = true;
                Logger.LogInfo("Headlook recentered");
            }
        }

        void LateUpdate()
        {
            if (!_enabled) return;
            Camera cam = Camera.main;
            if (cam == null)
            {
                Camera[] all = Camera.allCameras;
                if (all.Length > 0) cam = all[0];
            }
            if (cam == null) return;

            // The tracker only sends while it sees a face. With no recent packet (face lost,
            // tracker not started yet or closed) ease back to looking forward instead of
            // freezing at the last angle.
            bool fresh = _gotPacket && unchecked(Environment.TickCount - _lastRxTick) < STALE_MS;

            float dy = 0f, dp = 0f;
            if (fresh)
            {
                // neutral = the first pose we actually receive (or Shift+K)
                if (!_haveNeutral) { _nYaw = _yaw; _nPitch = _pitch; _haveNeutral = true; }
                // DeltaAngle wraps at +-180 so a pose near that edge can't flip the view
                dy = Mathf.Clamp(Mathf.DeltaAngle(_nYaw, _yaw) * _gainYaw.Value, -_maxYaw.Value, _maxYaw.Value);
                dp = Mathf.Clamp(Mathf.DeltaAngle(_nPitch, _pitch) * _gainPitch.Value, -_maxPitch.Value, _maxPitch.Value);
                if (_invertYaw.Value) dy = -dy;
                if (_invertPitch.Value) dp = -dp;
            }

            float a = Mathf.Clamp01(_smooth.Value);
            _sYaw = a * _sYaw + (1f - a) * dy;
            _sPitch = a * _sPitch + (1f - a) * dp;

            // additive look offset in camera-local space, on top of the game's camera pose
            cam.transform.rotation = cam.transform.rotation * Quaternion.Euler(-_sPitch, _sYaw, 0f);
        }
    }
}
