import os

from nostr_sdk import Keys

from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.output_utils import PostProcessFunctionType
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys


class DVMConfig:
    SUPPORTED_DVMS = []
    PRIVATE_KEY: str = ""
    PUBLIC_KEY: str = ""
    FIX_COST: float = None
    PER_UNIT_COST: float = None


    RELAY_LIST = ["wss://relay.damus.io", "wss://nos.lol", "wss://nostr.wine",
                  "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
                  "wss://relay.f7z.io", "wss://pablof7z.nostr1.com", "wss://relay.nostr.net", "wss://140.f7z.io",
                  "wss://relay.snort.social", "wss://offchain.pub/", "wss://relay.nostr.band"]

    RELAY_TIMEOUT = 5
    EXTERNAL_POST_PROCESS_TYPE = PostProcessFunctionType.NONE  # Leave this on None, except the DVM is external
    LNBITS_INVOICE_KEY = '' # Will all automatically generated by default, or read from .env
    LNBITS_ADMIN_KEY = ''  # In order to pay invoices, e.g. from the bot to DVMs, or reimburse users.
    LNBITS_URL = 'https://lnbits.com'
    LN_ADDRESS = ''
    SCRIPT = ''
    IDENTIFIER = ''
    USE_OWN_VENV = True # Make an own venv for each dvm's process function.Disable if you want to install packages into main venv. Only recommended if you dont want to run dvms with different dependency versions
    DB: str
    NEW_USER_BALANCE: int = 0  # Free credits for new users
    NIP88: NIP88Config
    NIP89: NIP89Config
    SEND_FEEDBACK_EVENTS = True
    SHOW_RESULT_BEFORE_PAYMENT: bool = False  # if this is true show results even when not paid right after autoprocess
    SCHEDULE_UPDATES_SECONDS = 0

def build_default_config(identifier):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    dvm_config.IDENTIFIER = identifier
    npub = Keys.parse(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    dvm_config.LNBITS_INVOICE_KEY = invoice_key
    dvm_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.LN_ADDRESS = lnaddress
    return dvm_config
