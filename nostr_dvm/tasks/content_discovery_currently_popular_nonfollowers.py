import json
import json
import os
from datetime import timedelta

from nostr_sdk import Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, NostrDatabase, \
    ClientBuilder, Filter, SyncOptions, SyncDirection, init_logger, LogLevel, Kind, \
    RelayLimits

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils import definitions
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config, check_and_set_d_tag_nip88, check_and_set_tiereventid_nip88
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag, create_amount_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events

"""
This File contains a Module to discover popular notes by topics
Accepted Inputs: none
Outputs: A list of events 
Params:  None
"""


class DicoverContentCurrentlyPopularNonFollowers(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "discover-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    request_form = None
    last_schedule: int
    min_reactions = 2
    db_since = 10 * 3600
    db_name = "db/nostr_default_recent_notes.db"
    search_list = []
    avoid_list = []
    must_list = []
    personalized = True
    result = ""
    database = None

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):

        if dvm_config.DATABASE is not None:
            self.database = dvm_config.DATABASE

        self.request_form = {"jobID": "generic"}
        opts = {
            "max_results": 200,
        }
        self.request_form['options'] = json.dumps(opts)

        dvm_config.SCRIPT = os.path.abspath(__file__)

        if self.options.get("personalized"):
            self.personalized = bool(self.options.get("personalized"))
        self.last_schedule = Timestamp.now().as_secs()
        if self.options.get("search_list"):
            self.search_list = self.options.get("search_list")
            # print(self.search_list)
        if self.options.get("avoid_list"):
            self.avoid_list = self.options.get("avoid_list")
        if self.options.get("must_list"):
            self.must_list = self.options.get("must_list")
        if self.options.get("db_name"):
            self.db_name = self.options.get("db_name")
        if self.options.get("db_since"):
            self.db_since = int(self.options.get("db_since"))

        use_logger = False
        if use_logger:
            init_logger(LogLevel.DEBUG)

        if self.dvm_config.UPDATE_DATABASE:
            await self.sync_db()
        if not self.personalized:
            self.result = await self.calculate_result(self.request_form)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config

        request_form = {"jobID": event.id().to_hex()}
        user = event.author().to_hex()
        # default values
        max_results = 200

        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "max_results":  # check for param type
                    max_results = int(tag.as_vec()[2])
                elif param == "user":  # check for param type
                    user = tag.as_vec()[2]

        options = {
            "max_results": max_results,
            "user": user,
        }
        request_form['options'] = json.dumps(options)
        self.request_form = request_form
        return request_form

    async def process(self, request_form):
        # if the dvm supports individual results, recalculate it every time for the request
        if self.personalized:
            return await self.calculate_result(request_form)
        # else return the result that gets updated once every schenduled update. In this case on database update.
        else:
            return self.result

    async def post_process(self, result, event):
        """Overwrite the interface function to return a social client readable format, if requested"""
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'output':
                format = tag.as_vec()[1]
                if format == "text/plain":  # check for output type
                    result = post_process_list_to_events(result)

        # if not text/plain, don't post-process
        return result

    async def calculate_result(self, request_form):
        from nostr_sdk import Filter
        from types import SimpleNamespace
        ns = SimpleNamespace()

        options = self.set_options(request_form)
        relaylimits = RelayLimits.disable()
        opts = (
            Options().relay_limits(relaylimits))
        sk = SecretKey.parse(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        if self.database is None:
            self.database = NostrDatabase.lmdb(self.db_name)

        cli = ClientBuilder().database(self.database).signer(NostrSigner.keys(keys)).opts(opts).build()
        for relay in self.dvm_config.SYNC_DB_RELAY_LIST:
            await cli.add_relay(relay)

        # ropts = RelayOptions().ping(False)
        # cli.add_relay_with_opts("wss://nostr.band", ropts)

        await cli.connect()
        user = PublicKey.parse(options["user"])
        followers_filter = Filter().author(user).kinds([Kind(3)])
        followers = await cli.fetch_events(followers_filter, relay_timeout)
        if len(followers.to_vec()) > 0:
            newest = 0
            best_entry = followers.to_vec()[0]
            for entry in followers.to_vec():
                if entry.created_at().as_secs() > newest:
                    newest = entry.created_at().as_secs()
                    best_entry = entry

            # print(best_entry.as_json())
            followings = []
            for tag in best_entry.tags().to_vec():
                if tag.as_vec()[0] == "p":
                    following = tag.as_vec()[1]
                    followings.append(following)
        else:
            print("Couldn't find follower List")
            return []

        print(len(followings))

        timestamp_since = Timestamp.now().as_secs() - self.db_since
        since = Timestamp.from_secs(timestamp_since)

        filter1 = Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(since)

        events = await self.database.query(filter1)

        print("[" + self.dvm_config.NIP89.NAME + "] Considering " + str(len(events.to_vec())) + " Events")
        ns.finallist = {}

        for event in events.to_vec():
            if event.author().to_hex() in followings:
                continue

            filt = Filter().kinds(
                [definitions.EventDefinitions.KIND_ZAP, definitions.EventDefinitions.KIND_REACTION,
                 definitions.EventDefinitions.KIND_REPOST,
                 definitions.EventDefinitions.KIND_NOTE]).event(event.id()).since(since)
            reactions = await self.database.query(filt)
            if len(reactions.to_vec()) >= self.min_reactions:
                ns.finallist[event.id().to_hex()] = len(reactions.to_vec())

        print(len(ns.finallist))
        result_list = []
        finallist_sorted = sorted(ns.finallist.items(), key=lambda x: x[1], reverse=True)[:int(options["max_results"])]
        for entry in finallist_sorted:
            # print(EventId.parse(entry[0]).to_bech32() + "/" + EventId.parse(entry[0]).to_hex() + ": " + str(entry[1]))
            e_tag = Tag.parse(["e", entry[0]])
            result_list.append(e_tag.as_vec())
        if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
            print("[" + self.dvm_config.NIP89.NAME + "] Filtered " + str(
                len(result_list)) + " fitting events.")
        # await cli.shutdown()
        return json.dumps(result_list)

    async def schedule(self, dvm_config):
        if dvm_config.SCHEDULE_UPDATES_SECONDS == 0:
            return 0
        else:
            if Timestamp.now().as_secs() >= self.last_schedule + dvm_config.SCHEDULE_UPDATES_SECONDS:
                if self.dvm_config.UPDATE_DATABASE:
                    await self.sync_db()
                self.last_schedule = Timestamp.now().as_secs()
                return 1

    async def sync_db(self):
        try:
            sk = SecretKey.parse(self.dvm_config.PRIVATE_KEY)
            keys = Keys.parse(sk.to_hex())
            database = NostrDatabase.lmdb(self.db_name)
            cli = ClientBuilder().signer(NostrSigner.keys(keys)).database(database).build()

            for relay in self.dvm_config.SYNC_DB_RELAY_LIST:
                await cli.add_relay(relay)

            await cli.connect()

            timestamp_since = Timestamp.now().as_secs() - self.db_since
            since = Timestamp.from_secs(timestamp_since)

            filter1 = Filter().kinds(
                [definitions.EventDefinitions.KIND_NOTE, definitions.EventDefinitions.KIND_REACTION,
                 definitions.EventDefinitions.KIND_ZAP]).since(since)  # Notes, reactions, zaps

            # filter = Filter().author(keys.public_key())
            if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                print("[" + self.dvm_config.NIP89.NAME + "] Syncing notes of the last " + str(
                    self.db_since) + " seconds.. this might take a while..")
            dbopts = SyncOptions().direction(SyncDirection.DOWN)
            await cli.sync(filter1, dbopts)
            await cli.database().delete(Filter().until(Timestamp.from_secs(
                Timestamp.now().as_secs() - self.db_since)))  # Clear old events so db doesn't get too full.
            await cli.shutdown()
            if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                print(
                    "[" + self.dvm_config.NIP89.NAME + "] Done Syncing Notes of the last " + str(
                        self.db_since) + " seconds..")
        except Exception as e:
            print(e)


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config, options, image, description, update_rate=600, cost=0,
                  processing_msg=None, update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    # Activate these to use a subscription based model instead
    # dvm_config.SUBSCRIPTION_REQUIRED = True
    # dvm_config.SUBSCRIPTION_DAILY_COST = 1
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": description,
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "personalized": False,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 100)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    return DicoverContentCurrentlyPopularNonFollowers(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                      admin_config=admin_config, options=options)


def build_example_subscription(name, identifier, admin_config, options, image, description, processing_msg=None,
                               update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = 600  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    # Activate these to use a subscription based model instead
    dvm_config.FIX_COST = 0
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": description,
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "subscription": True,
        "personalized": False,
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 100)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    nip88config = NIP88Config()
    nip88config.DTAG = check_and_set_d_tag_nip88(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip88config.TIER_EVENT = check_and_set_tiereventid_nip88(identifier, "1")
    nip89config.NAME = name
    nip88config.IMAGE = nip89info["picture"]
    nip88config.TITLE = name
    nip88config.AMOUNT_DAILY = 100
    nip88config.AMOUNT_MONTHLY = 2000
    nip88config.CONTENT = "Subscribe to the DVM for unlimited use during your subscription"
    nip88config.PERK1DESC = "Unlimited requests"
    nip88config.PERK2DESC = "Support NostrDVM & NostrSDK development"
    nip88config.PAYMENT_VERIFIER_PUBKEY = "5b5c045ecdf66fb540bdf2049fe0ef7f1a566fa427a4fe50d400a011b65a3a7e"

    # admin_config.FETCH_NIP88 = True
    # admin_config.EVENTID = "63a791cdc7bf78c14031616963105fce5793f532bb231687665b14fb6d805fdb"
    # admin_config.PRIVKEY = dvm_config.PRIVATE_KEY

    return DicoverContentCurrentlyPopularNonFollowers(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                      nip88config=nip88config,
                                                      admin_config=admin_config,
                                                      options=options)


if __name__ == '__main__':
    process_venv(DicoverContentCurrentlyPopularNonFollowers)
