# ADMINISTRARIVE DB MANAGEMENT

from nostr_sdk import Keys, PublicKey, Client

from nostr_dvm.utils.database_utils import get_from_sql_table, list_db, delete_from_sql_table, update_sql_table, \
    get_or_add_user, clean_db
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip88_utils import nip88_announce_tier, fetch_nip88_parameters_for_deletion, fetch_nip88_event, \
    check_and_set_tiereventid_nip88
from nostr_dvm.utils.nip89_utils import nip89_announce_tasks, fetch_nip89_parameters_for_deletion
from nostr_dvm.utils.nostr_utils import update_profile


class AdminConfig:
    REBROADCAST_NIP89: bool = False
    REBROADCAST_NIP88: bool = False
    UPDATE_PROFILE: bool = False
    DELETE_NIP89: bool = False
    DELETE_NIP88: bool = False
    FETCH_NIP88: bool = False
    WHITELISTUSER: bool = False
    UNWHITELISTUSER: bool = False
    BLACKLISTUSER: bool = False
    DELETEUSER: bool = False
    LISTDATABASE: bool = False
    ClEANDB: bool = False
    INDEX: str = "1"

    USERNPUBS: list = []

    EVENTID: str = ""
    PRIVKEY: str = ""


def admin_make_database_updates(adminconfig: AdminConfig = None, dvmconfig: DVMConfig = None, client: Client = None):
    # This is called on start of Server, Admin function to manually whitelist/blacklist/add balance/delete users
    if adminconfig is None or dvmconfig is None:
        return

    if not isinstance(adminconfig, AdminConfig):
        return

    if ((
            adminconfig.WHITELISTUSER is True or adminconfig.UNWHITELISTUSER is True or adminconfig.BLACKLISTUSER is True or adminconfig.DELETEUSER is True)
            and adminconfig.USERNPUBS == []):
        return

    if adminconfig.UPDATE_PROFILE and (dvmconfig.NIP89 is None):
        return

    if adminconfig.DELETE_NIP89 and (adminconfig.EVENTID == "" or adminconfig.EVENTID == ""):
        return

    db = dvmconfig.DB

    for npub in adminconfig.USERNPUBS:
        if str(npub).startswith("npub"):
            publickey = PublicKey.from_bech32(npub).to_hex()
        else:
            publickey = npub

        if adminconfig.WHITELISTUSER:
            user = get_or_add_user(db, publickey, client=client, config=dvmconfig)
            update_sql_table(db, user.npub, user.balance, True, False, user.nip05, user.lud16, user.name, user.lastactive, user.subscribed)
            user = get_from_sql_table(db, publickey)
            print(str(user.name) + " is whitelisted: " + str(user.iswhitelisted))

        if adminconfig.UNWHITELISTUSER:
            user = get_from_sql_table(db, publickey)
            update_sql_table(db, user.npub, user.balance, False, False, user.nip05, user.lud16, user.name, user.lastactive, user.subscribed)

        if adminconfig.BLACKLISTUSER:
            user = get_from_sql_table(db, publickey)
            update_sql_table(db, user.npub, user.balance, False, True, user.nip05, user.lud16, user.name, user.lastactive, user.subscribed)

        if adminconfig.DELETEUSER:
            delete_from_sql_table(db, publickey)

    if adminconfig.ClEANDB:
        clean_db(db)

    if adminconfig.LISTDATABASE:
        list_db(db)

    if adminconfig.REBROADCAST_NIP89:
        nip89_announce_tasks(dvmconfig, client=client)

    if adminconfig.REBROADCAST_NIP88:
        annotier_id = nip88_announce_tier(dvmconfig, client=client)
        check_and_set_tiereventid_nip88(dvmconfig.IDENTIFIER, adminconfig.INDEX, annotier_id.to_hex())

    if adminconfig.DELETE_NIP89:
        event_id = adminconfig.EVENTID
        keys = Keys.parse(
            adminconfig.PRIVKEY)  # Private key from sender of Event (e.g. the key of an nip89 announcement you want to delete)
        fetch_nip89_parameters_for_deletion(keys, event_id, client, dvmconfig)

    if adminconfig.DELETE_NIP88:
        event_id = adminconfig.EVENTID
        keys = Keys.parse(
            adminconfig.PRIVKEY)  # Private key from sender of Event (e.g. the key of an nip89 announcement you want to delete)
        fetch_nip88_parameters_for_deletion(keys, event_id, client, dvmconfig)

    if adminconfig.FETCH_NIP88:
        event_id = adminconfig.EVENTID
        keys = Keys.parse(
            adminconfig.PRIVKEY)
        fetch_nip88_event(keys, event_id, client, dvmconfig)

    if adminconfig.UPDATE_PROFILE:
        update_profile(dvmconfig, client, lud16=dvmconfig.LN_ADDRESS)
