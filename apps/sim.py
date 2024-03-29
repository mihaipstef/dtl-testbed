from gnuradio import (analog,
                      blocks,
                      channels,
                      dtl,
                      gr,
                      testbed)
import os
import sys
from testbed import (
    app,
    testbed_io,
)


current_module = sys.modules[__name__]


class ofdm_adaptive_full_duplex_sim(app.dtl_app):
    """
    OFDM Adaptive Full Duplex Simulator
    """

    def __init__(self, config_dict, run_config_file):
        super().__init__(config_dict, run_config_file)
        ofdm_config = config_dict.get("ofdm_config", {})
        config_path = f"{os.path.dirname(current_module.__file__)}/config"
        if "fec_codes" in ofdm_config and len(ofdm_config["fec_codes"]):
            ofdm_config["fec_codes"] = [(name, f"{config_path}/{fn}")
                                        for name, fn in ofdm_config["fec_codes"]]
        self.samp_rate = samp_rate = config_dict.get("sample_rate", 200000)
        self.n_bytes = 100
        self.direct_channel_noise_level = 0.0001
        self.direct_channel_freq_offset = 0.5
        self.fft_len = 64
        self.cp_len = 16
        self.run_config_file = run_config_file
        self.use_sync_correct = ofdm_config.get("use_sync_correct", True)
        self.max_doppler = 0
        self.propagation_paths = config_dict.get(
            "propagation_paths", [(0, 0, 0, 1)])
        self.frame_length = ofdm_config.get("frame_length", 20)
        self.frame_samples = (self.frame_length + 4) * \
            (self.fft_len + self.cp_len)
        self.data_bytes = config_dict.get("data_bytes", None)
        self.len_key = "len_key"
        self.ifaces_base = config_dict.get("env_mode", "netio")

        ##################################################
        # Blocks
        ##################################################

        self.io1 = testbed_io.tuntap(f"{self.ifaces_base}0", 65000, 2048, self.len_key, testbed.transported_protocol_t.MODIFIED_ETHER)
        self.io2 = testbed_io.tuntap(f"{self.ifaces_base}1", 65000, 2048, self.len_key, testbed.transported_protocol_t.MODIFIED_ETHER)

        self.modem1 = dtl.ofdm_adaptive_full_duplex.from_parameters(
            config_dict=ofdm_config,
            name="m0",
            fft_len=self.fft_len,
            cp_len=self.cp_len,
            rolloff=0,
            scramble_bits=False,
            use_sync_correct=self.use_sync_correct,
            frame_length=self.frame_length,
            packet_length_tag_key=self.len_key,
        )
        self.modem2 = dtl.ofdm_adaptive_full_duplex.from_parameters(
            config_dict=ofdm_config,
            name="m1",
            fft_len=self.fft_len,
            cp_len=self.cp_len,
            rolloff=0,
            scramble_bits=False,
            use_sync_correct=self.use_sync_correct,
            frame_length=self.frame_length,
            packet_length_tag_key=self.len_key,
        )
        delays, delays_std, delays_maxdev, mags = zip(*self.propagation_paths)
        self.fadding_channel = channels.selective_fading_model2(
            8, self.max_doppler, False, 4.0, 0, delays, delays_std, delays_maxdev, mags, 8)
        self.awgn_channel = channels.channel_model(
            noise_voltage=0.0,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=[1.0 + 1.0j],
            noise_seed=0,
            block_tags=True)
        self.throtle = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate, True)

        self.msg_debug = blocks.message_debug(True)
        monitor_address = config_dict.get(
            "monitor_probe", "tcp://127.0.0.1:5555")
        monitor_probe_name = config_dict.get("monitor_probe_name", "probe")

        self.monitor_probe = testbed.monitor_probe(
            monitor_probe_name, testbed.message_sender(monitor_address, bind=False))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.throtle.set_sample_rate(self.samp_rate)
        self.fadding_channel.set_fDTs((0/self.samp_rate))

    def get_n_bytes(self):
        return self.n_bytes

    def set_n_bytes(self, n_bytes):
        self.n_bytes = n_bytes

    def set_direct_channel_noise_level(self, direct_channel_noise_level):
        self.direct_channel_noise_level = float(direct_channel_noise_level)
        self.awgn_channel.set_noise_voltage(self.direct_channel_noise_level)

    def set_direct_channel_freq_offset(self, direct_channel_freq_offset):
        self.direct_channel_freq_offset = direct_channel_freq_offset
        self.awgn_channel.set_frequency_offset(self.direct_channel_freq_offset)

    def set_max_doppler(self, val):
        self.max_doppler = val
        self.fadding_channel.set_fDTs(self.max_doppler)


    def wire_it(self):

        # Direct path
        self.connect(self.io1, (self.modem1, 0))
        self.connect((self.modem1, 0), self.io1)
        self.connect((self.modem2, 0), self.io2)
        self.connect(self.io2, (self.modem2, 0))

        self.connect(
            (self.modem1, 1),
            #(self.fadding_channel, 0),
            (self.awgn_channel, 0),
            (self.modem2, 1)
        )
        # Feedback path
        self.connect(
            (self.modem2, 1),
            (self.modem1, 1)
        )

        self.msg_connect((self.modem1, "monitor"),
                         (blocks.message_debug(True), "store"))
        self.msg_connect((self.modem2, "monitor"),
                         (blocks.message_debug(True), "store"))
        self.msg_connect((self.modem2, "monitor"), (self.monitor_probe, "in"))
        return self
