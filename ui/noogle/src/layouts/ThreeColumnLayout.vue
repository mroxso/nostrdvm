<script setup>
import Login from "@/components/Login.vue";
</script>

<template>

  <div className="navbar bg-base-100 scroll-auto">
    <div className="flex-none">

    </div>
    <div className="flex-1">
      <div class="scroll">
        <router-link class="menu" to="/">Search</router-link>
        <router-link class="menu" to="/discover">Discover</router-link>
        <router-link class="menu" to="/filter">Filter</router-link>
        <router-link class="menu" to="/image">Create</router-link>
        <router-link class="menu" to="/ai">AI</router-link>
        <router-link class="menu" to="/nip89">DVMs</router-link>
      </div>

    </div>
    <Login/>

  </div>

  <div class="three-column-layout">
    <header>

      <!-- <AppLogo />-->

    </header>

    <main>
      <router-view/>
      <slot/>
    </main>

    <aside>
      <slot name="aside"/>

    </aside>
    <footer>
      <!--<Donate style="margin-top: 4px"/> -->
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.three-column-layout {
  display: grid;
  grid-template-areas:
    "header"
    "main"
    "aside"
    "footer";

  div.scroll {
    margin: 4px;
    padding: 4px;
    background-color: #08c708;
    width: 300px;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
  }

  header {
    grid-area: header;
    margin-top: 30px;
  }

  main {

    grid-area: main;
    margin-top: 10px;
    margin-bottom: 100px;
    padding: 20px;

  }

  footer {

    position: fixed;
    bottom: 0;
    background: rgba(0, 0, 0, 0);;
    grid-area: footer;
    width: 100vw;
    height: 32px;

    z-index: 10;
    text-align: center;
  }

  aside {
    grid-area: aside;
    margin-top: 10px;
    padding: 20px;
  }


  .router-link-exact-active {
    color: rgba(255, 255, 255, 0.87);
  }


  .v-Button {
    @apply bg-black hover:bg-nostr focus:ring-nostr mb-2 inline-flex flex-none items-center rounded-lg border border-nostr px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

    height: 44px;
  }


  @media (min-width: 768px) {
    grid-template-columns: 1fr 3fr 1fr;
    grid-template-areas: "header main aside footer";
  }
}

</style>