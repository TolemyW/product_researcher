import unittest

from src.collect.channels import B2B_CHANNELS, CONSUMER_CHANNELS, SOFTWARE_CHANNELS, get_channels_for_product_type


class ChannelSelectionTests(unittest.TestCase):
    def test_default_channels_used_when_type_unknown(self) -> None:
        channels = get_channels_for_product_type(None)
        self.assertGreaterEqual(len(channels), 3)
        self.assertTrue(any(channel.name == "general" for channel in channels))

    def test_b2b_channels_present(self) -> None:
        channels = get_channels_for_product_type("b2b")
        names = [c.name for c in channels]
        for expected in [c.name for c in B2B_CHANNELS]:
            self.assertIn(expected, names)

    def test_consumer_and_software_use_specialized_channels(self) -> None:
        consumer_names = {c.name for c in get_channels_for_product_type("consumer")}
        software_names = {c.name for c in get_channels_for_product_type("software")}

        self.assertTrue(consumer_names.issuperset({c.name for c in CONSUMER_CHANNELS}))
        self.assertTrue(software_names.issuperset({c.name for c in SOFTWARE_CHANNELS}))


if __name__ == "__main__":
    unittest.main()
