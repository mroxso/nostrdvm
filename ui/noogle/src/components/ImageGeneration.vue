<script setup>


import {Event, EventBuilder, Filter, Keys, PublicKey, Tag, Timestamp} from "@rust-nostr/nostr-sdk";
import store from '../store';
import {ref} from "vue";
import ModalComponent from "../components/Newnote.vue";
import VueDatePicker from "@vuepic/vue-datepicker";
import {
  copyurl,
  dvmreactions,
  nextInput,
  post_note,
  schedule,
  sleep
} from "../components/helper/Helper.vue"
import {zap, get_invoice} from "../components/helper/Zap.vue"

import StringUtil from "@/components/helper/string.ts";


let dvms = []
let hasmultipleinputs = false
let requestids = []

async function generate_image(message) {

  listen()

  try {
    if (message === undefined) {
      message = "A purple Ostrich"
    }

    if (store.state.pubkey === undefined) {

      return
    }

    dvms = []
    store.commit('set_imagedvm_results', dvms)
    let client = store.state.client

    let content = "NIP 90 Image Generation request"
    let kind = 5100
    let tags = [
      Tag.parse(["i", message, "text"])
    ]

    let r = ["relays"]
    for (let relay of store.state.relays) {
      r.push(relay)
    }
    console.log(r)
    tags.push(Tag.parse(r))

    hasmultipleinputs = false
    if (urlinput.value !== "" && urlinput.value.startsWith('http')) {
      let imagetag = Tag.parse(["i", urlinput.value, "url"])
      tags.push(imagetag)
      hasmultipleinputs = true
      console.log(urlinput.value)
    }

    let res;
    let requestid;

    /*let tags_t = []
    for (let tag of tags){
      tag = Tag.parse(tag)
      console.log(tag.asVec())
      tags_t.push(tag) */

    let evt = new EventBuilder(kind, content, tags)
    let unsigned = evt.toUnsignedEvent(store.state.pubkey)
    let signedEvent = await (await client.signer()).signEvent(unsigned)
    console.log(signedEvent.id.toHex())
    requestid = signedEvent.id.toHex()
    requestids.push(requestid)
    store.commit('set_current_request_id_image', requestids)
    store.commit('set_image_command_sent', true)

    await client.sendEvent(signedEvent)


  } catch (error) {
    console.log(error);
  }
}

async function listen() {
  let client = store.state.client
  let pubkey = store.state.pubkey

  const filter = new Filter().kinds([7000, 6100, 6905]).pubkey(pubkey).since(Timestamp.now());
  await client.subscribe([filter]);

  const handle = {
    // Handle event
    handleEvent: async (relayUrl, subscriptionId, event) => {
      /* if (store.state.imagehasEventListener === false){
         return true
       }*/
      //const dvmname =  getNamefromId(event.author.toHex())
      console.log("Received new event from", relayUrl);
      // console.log(event.asJ())
      let resonsetorequest = false
      sleep(0).then(async () => {
        for (let tag in event.tags) {
          if (event.tags[tag].asVec()[0] === "e") {
            if (store.state.requestidImage.includes(event.tags[tag].asVec()[1])) {
              resonsetorequest = true
            }
          }

        }
        if (resonsetorequest === true) {
           store.commit('set_image_command_sent', false)
          if (event.kind === 7000) {



            try {
              //console.log("7000: ", event.content);
              //console.log("DVM: " + event.author.toHex())
              //miniToastr.showMessage("DVM: " + dvmname, event.content, VueNotifications.types.info)

              let status = "unknown"
              let jsonentry = {
                id: event.author.toHex(),
                event_id: event.id.toHex(),
                kind: "",
                status: status,
                result: "",
                name: event.author.toBech32(),
                about: "",
                image: "",
                amount: 0,
                bolt11: "",
                nip90params: {},

              }

              for (const tag in event.tags) {
                if (event.tags[tag].asVec()[0] === "status") {
                  status = event.tags[tag].asVec()[1]
                }

                if (event.tags[tag].asVec()[0] === "amount") {
                  jsonentry.amount = event.tags[tag].asVec()[1]
                  if (event.tags[tag].asVec().length > 2) {
                    jsonentry.bolt11 = event.tags[tag].asVec()[2]
                  } else {
                     jsonentry.bolt11 = ""
                  }

                }
              }

              //let dvm = store.state.nip89dvms.find(x => JSON.parse(x.event).pubkey === event.author.toHex())


              for (const el of store.state.nip89dvms) {
                if (JSON.parse(el.event).pubkey === event.author.toHex().toString() && el.kind === "5100") {
                  jsonentry.name = el.name
                  jsonentry.about = el.about
                  jsonentry.image = el.picture
                  jsonentry.nip90Params = el.nip90Params
                  jsonentry.reactions = await dvmreactions(PublicKey.parse(el.id), store.state.followings)
                  jsonentry.reactions.negativeUser = false
                  jsonentry.reactions.positiveUser = false
                  jsonentry.event = Event.fromJson(el.event)


                }
              }
              if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
                if (!hasmultipleinputs ||
                    (hasmultipleinputs && jsonentry.id !== "04f74530a6ede6b24731b976b8e78fb449ea61f40ff10e3d869a3030c4edc91f")) {
                  // DVM can not handle multiple inputs, straight up censorship until spec is fulfilled or requests are ignored.
                  dvms.push(jsonentry)
                }

              }

              dvms.find(i => i.id === jsonentry.id).status = status

              store.commit('set_imagedvm_results', dvms)


            } catch (error) {
              console.log("Error: ", error);
            }


          } else if (event.kind === 6905) {
            console.log(event.content)

          } else if (event.kind === 6100) {
            let entries = []
            console.log("6100:", event.content);


            for (const el of store.state.nip89dvms) {
              let status = "unknown"
              let jsonentry = {
                id: event.author.toHex(),
                event_id: event.id.toHex(),
                kind: "",
                status: status,
                result: "",
                name: "Not announced" + event.author.toBech32(),
                about: "",
                image: "",
                amount: 0,
                bolt11: "",
                nip90params: {},

              }
              if (JSON.parse(el.event).pubkey === event.author.toHex().toString() && el.kind === "5100") {
                jsonentry.name = el.name
                jsonentry.about = el.about
                jsonentry.image = el.picture
                jsonentry.nip90Params = el.nip90Params
                jsonentry.reactions = await dvmreactions(PublicKey.parse(el.id), store.state.followings)
                jsonentry.event = Event.fromJson(el.event)


              }

              if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
                dvms.push(jsonentry)
              }
            }
            //miniToastr.showMessage("DVM: " + dvmname, "Received Results", VueNotifications.types.success)
            dvms.find(i => i.id === event.author.toHex()).result = event.content
            dvms.find(i => i.id === event.author.toHex()).status = "finished"
            store.commit('set_imagedvm_results', dvms)
          }
        }
      })
    },

    handleMsg: async (relayUrl, message) => {
      //console.log("Received message from", relayUrl, message.asJson());
    }
  };

  client.handleNotifications(handle);
}


const urlinput = ref("");


async function zap_local(dvm) {
  if (dvm.bolt11 === ""){
    dvm.bolt11 = await get_invoice(dvm.id, dvm.event_id, dvm.amount)
  }
  let success = await zap(dvm.bolt11)
  if (success) {
    dvms.find(i => i.bolt11 === dvm.bolt11).status = "paid"
    store.commit('set_imagedvm_results', dvms)
  }
}


defineProps({
  msg: {
    type: String,
    required: false
  },
})


const isModalOpened = ref(false);
const modalcontent = ref("");
const datetopost = ref(Date.now());


const openModal = result => {
  datetopost.value = Date.now();
  isModalOpened.value = true;
  modalcontent.value = result
};
const closeModal = () => {
  isModalOpened.value = false;
  console.log(datetopost.value)
};

const submitHandler = async () => {
}


</script>
<template>

  <div class="greetings">
    <br>
    <br>
    <h1 class="text-7xl font-black tracking-wide">DVM</h1>
    <h1 class="text-7xl font-black tracking-wide">Image Generation</h1>
    <h2 class="text-base-200-content text-center tracking-wide text-2xl font-thin ">
      Generate Images, the decentralized way</h2>
    <h3>
      <br>
      <input v-model="message" autofocus class="c-Input" placeholder="A purple ostrich..."
             @keyup.enter="generate_image(message)" @keydown.enter="nextInput">
      <button class="v-Button" :disabled="store.state.image_command_sent === true"  @click="generate_image(message)">Generate Image</button>
    </h3>
    <details class="collapse bg-base " className="advanced">
      <summary class="collapse-title font-thin bg">Advanced Options</summary>
      <div id="collapse-settings" class="collapse-content font-size-0" className="z-10">
        <div>
          <h4 className="inline-flex flex-none font-thin">Url to existing image:</h4>
          <div className="inline-flex flex-none" style="width: 10px;"></div>
          <input v-model="urlinput" class="c-Input" placeholder="https://image.nostr.build/image123.jpg"
                 style="width: 300px;">
        </div>
      </div>
    </details>

     <div style="text-align: center">
      <button v-if="store.state.image_command_sent === true" :disabled="true" class="badge border-nostr">Waiting for Replies by DVMs, hold on. <span
          class="loading loading-infinity loading-md"></span></button>
    </div>
  </div>
  <br>


  <ModalComponent :isOpen="isModalOpened" name="first-modal" @submit="submitHandler" @modal-close="closeModal">
    <template #header>Share your creation on Nostr <br> <br></template>

    <template #content>
      <textarea v-model="modalcontent" className="d-Input" style="height: 300px;">{{modalcontent}}</textarea>
    </template>


    <template #footer>

      <div class="inline-flex flex-none">
        <VueDatePicker v-model="datetopost" :dark="true" :min-date="new Date()" className="bg-base-200"
                       style="max-width: 200px;" teleport-center></VueDatePicker>

      </div>

      <div class="content-center">
        <button className="v-Button" @click="schedule(modalcontent, datetopost)" @click.stop="closeModal"><img
            src="../../public/shipyard.ico" style="margin-right: 5px" width="25px"/>Schedule Note with Shipyard DVM
        </button>
        <br>
        or
        <br>
        <button className="v-Button" style="margin-bottom: 0px" @click="post_note(modalcontent)"
                @click.stop="closeModal"><img src="../../public/favicon.ico" style="margin-right: 5px;" width="25px"/>Post
          Note now
        </button>
      </div>
    </template>
  </ModalComponent>

  <div class="max-w-5xl relative space-y-3">
    <div class="grid grid-cols-1 gap-6">

      <div v-for="dvm in store.state.imagedvmreplies" :key="dvm.id"
           className="card w-70 bg-base-100 shadow-xl flex flex-col">


        <div className="card-body">

          <div className="playeauthor-wrapper">
            <figure className="w-20">
              <img :src="dvm.image" alt="DVM Picture" className="avatar"/>
            </figure>


            <h2 className="card-title">{{ dvm.name }}</h2>
          </div>
          <h3 class="fa-cut" v-html="StringUtil.parseHyperlinks(dvm.about)"></h3>
          <!-- <p>{{dvm.nip90Params}}</p> -->
          <!-- <div   v-for="param in dvm.nip90Params">
               <p>{{param}}</p>
             </div> -->


          <div className="card-actions justify-end mt-auto">

            <div className="tooltip mt-auto">


              <button v-if="dvm.status === 'processing'" className="btn">Processing</button>
              <button v-if="dvm.status === 'finished'" className="btn">Done</button>
              <button v-if="dvm.status === 'paid'" className="btn">Paid, waiting for DVM..</button>
              <button v-if="dvm.status === 'error'" className="btn">Error</button>
              <button v-if="dvm.status === 'payment-required'" className="zap-Button" @click="zap_local(dvm);">
                {{ dvm.amount / 1000 }} Sats
              </button>


            </div>

          </div>
          <figure className="w-full">
            <img v-if="dvm.result" :src="dvm.result" alt="DVM Picture" className="tooltip" data-top='Click to copy url'
                 height="200" @click="copyurl(dvm.result)"/>
          </figure>

          <div class="flex">


            <div
                v-if="dvm.result && store.state.pubkey.toHex() !== Keys.parse(store.state.nooglekey).publicKey.toHex()">
              <button aria-label="make note"
                      class="w-8 h-8 rounded-full bg-nostr border-white border-1 text-white flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-offset-2  focus:ring-black tooltip"
                      data-top='Share'
                      role="button" style="margin-right: 5px" @click="openModal('Look what I created on noogle.lol\n\n' +  dvm.result)">
                <svg class="icon icon-tabler icon-tabler-pencil" fill="none" height="20"
                     stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" viewBox="0 0 24 24"
                     width="20" xmlns="http://www.w3.org/2000/svg">
                  <path d="M0 0h24v24H0z" stroke="none"></path>
                  <path d="M4 20h4l10.5 -10.5a1.5 1.5 0 0 0 -4 -4l-10.5 10.5v4"></path>
                  <line x1="13.5" x2="17.5" y1="6.5" y2="10.5"></line>
                </svg>
              </button>

            </div>

            <div v-if="dvm.result && store.state.pubkey.toHex() !== Keys.parse(store.state.nooglekey).publicKey.toHex()"
                 style="margin-right: 5px">
              <!--                && !dvm.reactions.negativeUser && !dvm.reactions.positiveUser-->


              <!--                 <button @click="react_to_dvm(dvm, '👍')"  class="w-8 h-8 rounded-full bg-nostr border-white border-1 text-white flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-offset-2  focus:ring-black tooltip" data-top='Share' aria-label="make note" role="button">-->
              <!--                       <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-hand-thumbs-up" viewBox="0 0 16 16">-->
              <!--            <path d="M8.864.046C7.908-.193 7.02.53 6.956 1.466c-.072 1.051-.23 2.016-.428 2.59-.125.36-.479 1.013-1.04 1.639-.557.623-1.282 1.178-2.131 1.41C2.685 7.288 2 7.87 2 8.72v4.001c0 .845.682 1.464 1.448 1.545 1.07.114 1.564.415 2.068.723l.048.03c.272.165.578.348.97.484.397.136.861.217 1.466.217h3.5c.937 0 1.599-.477 1.934-1.064a1.86 1.86 0 0 0 .254-.912c0-.152-.023-.312-.077-.464.201-.263.38-.578.488-.901.11-.33.172-.762.004-1.149.069-.13.12-.269.159-.403.077-.27.113-.568.113-.857 0-.288-.036-.585-.113-.856a2 2 0 0 0-.138-.362 1.9 1.9 0 0 0 .234-1.734c-.206-.592-.682-1.1-1.2-1.272-.847-.282-1.803-.276-2.516-.211a10 10 0 0 0-.443.05 9.4 9.4 0 0 0-.062-4.509A1.38 1.38 0 0 0 9.125.111zM11.5 14.721H8c-.51 0-.863-.069-1.14-.164-.281-.097-.506-.228-.776-.393l-.04-.024c-.555-.339-1.198-.731-2.49-.868-.333-.036-.554-.29-.554-.55V8.72c0-.254.226-.543.62-.65 1.095-.3 1.977-.996 2.614-1.708.635-.71 1.064-1.475 1.238-1.978.243-.7.407-1.768.482-2.85.025-.362.36-.594.667-.518l.262.066c.16.04.258.143.288.255a8.34 8.34 0 0 1-.145 4.725.5.5 0 0 0 .595.644l.003-.001.014-.003.058-.014a9 9 0 0 1 1.036-.157c.663-.06 1.457-.054 2.11.164.175.058.45.3.57.65.107.308.087.67-.266 1.022l-.353.353.353.354c.043.043.105.141.154.315.048.167.075.37.075.581 0 .212-.027.414-.075.582-.05.174-.111.272-.154.315l-.353.353.353.354c.047.047.109.177.005.488a2.2 2.2 0 0 1-.505.805l-.353.353.353.354c.006.005.041.05.041.17a.9.9 0 0 1-.121.416c-.165.288-.503.56-1.066.56z"/>-->
              <!--          </svg>-->
              <!--                 </button>-->
              <!--          </div>-->


              <!--                <div  v-if="dvm.result && store.state.pubkey.toHex() !== Keys.parse(store.state.nooglekey).publicKey.toHex() && !dvm.reactions.negativeUser && !dvm.reactions.positiveUser" >-->
              <!--                 <button @click="react_to_dvm(dvm, '👎')"  class="w-8 h-8 rounded-full bg-nostr border-white border-1 text-white flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-offset-2  focus:ring-black tooltip" data-top='Share' aria-label="make note" role="button">-->
              <!--            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-hand-thumbs-down" viewBox="0 0 16 16">-->
              <!--  <path d="M8.864 15.674c-.956.24-1.843-.484-1.908-1.42-.072-1.05-.23-2.015-.428-2.59-.125-.36-.479-1.012-1.04-1.638-.557-.624-1.282-1.179-2.131-1.41C2.685 8.432 2 7.85 2 7V3c0-.845.682-1.464 1.448-1.546 1.07-.113 1.564-.415 2.068-.723l.048-.029c.272-.166.578-.349.97-.484C6.931.08 7.395 0 8 0h3.5c.937 0 1.599.478 1.934 1.064.164.287.254.607.254.913 0 .152-.023.312-.077.464.201.262.38.577.488.9.11.33.172.762.004 1.15.069.13.12.268.159.403.077.27.113.567.113.856s-.036.586-.113.856c-.035.12-.08.244-.138.363.394.571.418 1.2.234 1.733-.206.592-.682 1.1-1.2 1.272-.847.283-1.803.276-2.516.211a10 10 0 0 1-.443-.05 9.36 9.36 0 0 1-.062 4.51c-.138.508-.55.848-1.012.964zM11.5 1H8c-.51 0-.863.068-1.14.163-.281.097-.506.229-.776.393l-.04.025c-.555.338-1.198.73-2.49.868-.333.035-.554.29-.554.55V7c0 .255.226.543.62.65 1.095.3 1.977.997 2.614 1.709.635.71 1.064 1.475 1.238 1.977.243.7.407 1.768.482 2.85.025.362.36.595.667.518l.262-.065c.16-.04.258-.144.288-.255a8.34 8.34 0 0 0-.145-4.726.5.5 0 0 1 .595-.643h.003l.014.004.058.013a9 9 0 0 0 1.036.157c.663.06 1.457.054 2.11-.163.175-.059.45-.301.57-.651.107-.308.087-.67-.266-1.021L12.793 7l.353-.354c.043-.042.105-.14.154-.315.048-.167.075-.37.075-.581s-.027-.414-.075-.581c-.05-.174-.111-.273-.154-.315l-.353-.354.353-.354c.047-.047.109-.176.005-.488a2.2 2.2 0 0 0-.505-.804l-.353-.354.353-.354c.006-.005.041-.05.041-.17a.9.9 0 0 0-.121-.415C12.4 1.272 12.063 1 11.5 1"/>-->
              <!--</svg>-->
              <!--                 </button>-->

            </div>

          </div>

          <div>
            <!--            <p class="flex"> {{dvm.reactions.positiveUser.length}}-->


            <div>

              <!--        <div className="dropdown">-->
              <!--           <div tabIndex={0} role="button" class="button" >-->
              <!--           <svg style="margin-left: 3px; margin-right: 10px; margin-top: 3px" xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-hand-thumbs-up" viewBox="0 0 16 16">-->
              <!--            <path d="M8.864.046C7.908-.193 7.02.53 6.956 1.466c-.072 1.051-.23 2.016-.428 2.59-.125.36-.479 1.013-1.04 1.639-.557.623-1.282 1.178-2.131 1.41C2.685 7.288 2 7.87 2 8.72v4.001c0 .845.682 1.464 1.448 1.545 1.07.114 1.564.415 2.068.723l.048.03c.272.165.578.348.97.484.397.136.861.217 1.466.217h3.5c.937 0 1.599-.477 1.934-1.064a1.86 1.86 0 0 0 .254-.912c0-.152-.023-.312-.077-.464.201-.263.38-.578.488-.901.11-.33.172-.762.004-1.149.069-.13.12-.269.159-.403.077-.27.113-.568.113-.857 0-.288-.036-.585-.113-.856a2 2 0 0 0-.138-.362 1.9 1.9 0 0 0 .234-1.734c-.206-.592-.682-1.1-1.2-1.272-.847-.282-1.803-.276-2.516-.211a10 10 0 0 0-.443.05 9.4 9.4 0 0 0-.062-4.509A1.38 1.38 0 0 0 9.125.111zM11.5 14.721H8c-.51 0-.863-.069-1.14-.164-.281-.097-.506-.228-.776-.393l-.04-.024c-.555-.339-1.198-.731-2.49-.868-.333-.036-.554-.29-.554-.55V8.72c0-.254.226-.543.62-.65 1.095-.3 1.977-.996 2.614-1.708.635-.71 1.064-1.475 1.238-1.978.243-.7.407-1.768.482-2.85.025-.362.36-.594.667-.518l.262.066c.16.04.258.143.288.255a8.34 8.34 0 0 1-.145 4.725.5.5 0 0 0 .595.644l.003-.001.014-.003.058-.014a9 9 0 0 1 1.036-.157c.663-.06 1.457-.054 2.11.164.175.058.45.3.57.65.107.308.087.67-.266 1.022l-.353.353.353.354c.043.043.105.141.154.315.048.167.075.37.075.581 0 .212-.027.414-.075.582-.05.174-.111.272-.154.315l-.353.353.353.354c.047.047.109.177.005.488a2.2 2.2 0 0 1-.505.805l-.353.353.353.354c.006.005.041.05.041.17a.9.9 0 0 1-.121.416c-.165.288-.503.56-1.066.56z"/>-->
              <!--          </svg>-->
              <!--             </div>-->
              <!--      <div tabIndex={0} className="dropdown-content -start-56 z-[1] horizontal card card-compact w-64 p-2 shadow bg-nostr text-primary-content">-->
              <!--        <div className="card-body">-->
              <!--          <h3 className="card-title">Liked results by</h3>-->
              <!--            <div class="flex" >-->
              <!--           <div  v-for="user in dvm.reactions.positive">-->
              <!--                <div className="wotplayeauthor-wrapper">-->
              <!--                  <figure>-->
              <!--                       <img className="wotavatar" v-if="user.profile && user.profile.picture" :src="user.profile.picture"  onerror="this.src='https://noogle.lol/favicon.ico'" alt="DVM Picture" />-->
              <!--                     <img class="wotavatar" v-else src="@/assets/nostr-purple.svg" />-->
              <!--                  </figure>-->
              <!--                </div>-->
              <!--              </div>-->

            </div>


          </div>
        </div>
      </div>
      <!--<p>{{ this.current_user }}</p> -->
    </div>


    <div style="width: 10px"></div>

    <!--              {{dvm.reactions.negative.length}}-->
    <!--     <div>-->

    <!--        <div className="dropdown">-->
    <!--           <div tabIndex={0} role="button" class="button" >-->
    <!--                       <svg  style="margin-left: 3px; margin-top: 3px" xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-hand-thumbs-down" viewBox="0 0 16 16">-->
    <!--  <path d="M8.864 15.674c-.956.24-1.843-.484-1.908-1.42-.072-1.05-.23-2.015-.428-2.59-.125-.36-.479-1.012-1.04-1.638-.557-.624-1.282-1.179-2.131-1.41C2.685 8.432 2 7.85 2 7V3c0-.845.682-1.464 1.448-1.546 1.07-.113 1.564-.415 2.068-.723l.048-.029c.272-.166.578-.349.97-.484C6.931.08 7.395 0 8 0h3.5c.937 0 1.599.478 1.934 1.064.164.287.254.607.254.913 0 .152-.023.312-.077.464.201.262.38.577.488.9.11.33.172.762.004 1.15.069.13.12.268.159.403.077.27.113.567.113.856s-.036.586-.113.856c-.035.12-.08.244-.138.363.394.571.418 1.2.234 1.733-.206.592-.682 1.1-1.2 1.272-.847.283-1.803.276-2.516.211a10 10 0 0 1-.443-.05 9.36 9.36 0 0 1-.062 4.51c-.138.508-.55.848-1.012.964zM11.5 1H8c-.51 0-.863.068-1.14.163-.281.097-.506.229-.776.393l-.04.025c-.555.338-1.198.73-2.49.868-.333.035-.554.29-.554.55V7c0 .255.226.543.62.65 1.095.3 1.977.997 2.614 1.709.635.71 1.064 1.475 1.238 1.977.243.7.407 1.768.482 2.85.025.362.36.595.667.518l.262-.065c.16-.04.258-.144.288-.255a8.34 8.34 0 0 0-.145-4.726.5.5 0 0 1 .595-.643h.003l.014.004.058.013a9 9 0 0 0 1.036.157c.663.06 1.457.054 2.11-.163.175-.059.45-.301.57-.651.107-.308.087-.67-.266-1.021L12.793 7l.353-.354c.043-.042.105-.14.154-.315.048-.167.075-.37.075-.581s-.027-.414-.075-.581c-.05-.174-.111-.273-.154-.315l-.353-.354.353-.354c.047-.047.109-.176.005-.488a2.2 2.2 0 0 0-.505-.804l-.353-.354.353-.354c.006-.005.041-.05.041-.17a.9.9 0 0 0-.121-.415C12.4 1.272 12.063 1 11.5 1"/>-->
    <!--</svg>-->
    <!--             </div>-->
    <!--      <div tabIndex={0} className="dropdown-content -start-56 z-[1] horizontal card card-compact w-64 p-2 shadow bg-nostr text-primary-content">-->
    <!--        <div className="card-body">-->
    <!--          <h3 className="card-title">Disliked results by</h3>-->
    <!--            <div class="flex" >-->
    <!--           <div  v-for="user in dvm.reactions.negative">-->
    <!--                <div className="wotplayeauthor-wrapper">-->

    <!--                      <figure>-->

    <!--                       <img className="wotavatar" v-if="user.profile && user.profile.picture" :src="user.profile.picture"  onerror="this.src='https://noogle.lol/favicon.ico'" alt="DVM Picture" />-->
    <!--                     <img class="wotavatar" v-else src="@/assets/nostr-purple.svg" />-->
    <!--                  </figure>-->


    <!--                </div>-->
    <!--              </div>-->

    <!--</div>-->


    <!--        </div>-->
    <!--      </div>-->
    <!--    </div>-->
    <!--        &lt;!&ndash;<p>{{ this.current_user }}</p> &ndash;&gt;-->
    <!--     </div>-->


  </div>


  <!--           </div>-->

  <!--      </div>-->
  <!--    </div>-->
  <!--  </div>-->
</template>

<style scoped>

.zap-Button {
  @apply btn hover:bg-amber-400 border-amber-400 text-base;
  bottom: 0;
}

.v-Button {
  @apply bg-nostr hover:bg-nostr2 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-black px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
  height: 48px;
  margin: 5px;
}

.c-Input {
  @apply bg-base-200 text-accent dark:bg-black dark:text-white  focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  width: 350px;
  height: 48px;

}

.d-Input {
  @apply bg-black hover:bg-gray-900 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
  width: 500px;

  color: white;
  background: black;
}

.playeauthor-wrapper {
  padding: 6px;
  display: flex;
  align-items: center;
  justify-items: center;
}

.logo {
  display: flex;
  width: 100%;
  height: 125px;
  justify-content: center;
  align-items: center;
}

h3 {
  font-size: 1.0rem;
  text-align: left;
}


.avatar {
  margin-right: 10px;
  margin-left: 0px;
  display: inline-block;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: inset 0 4px 4px 0 rgb(0 0 0 / 10%);
}

.wotplayeauthor-wrapper {
  padding: 0px;
  display: flex;;
}

.wotavatar {
  margin-right: 0px;
  margin-left: 0px;

  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: inset 0 4px 4px 0 rgb(0 0 0 / 10%);
}

.greetings h1,
.greetings h3 {
  text-align: left;

}

@media (min-width: 1024px) {

  .greetings h1,
  .greetings h3 {
    text-align: center;
  }
}
</style>
