// get data left for us in the Django template
const container = '#forum-app';
const forum_base_url = JSON.parse(document.getElementById('forum-url').textContent);
const initial_data = JSON.parse(document.getElementById('initial-data').textContent);

const ThreadSummary = {
  name: 'ThreadSummary',
  components: [],
  props: ['thread'],
  template: `<li>#{{thread.number}} <router-link v-bind:to="'/' + thread.number">{{thread.title}}</router-link> by {{thread.author}}</li>`
};

const ThreadList = {
  name: 'ThreadList',
  components: {ThreadSummary},
  props: [],
  computed: {
    threadList () {
      return this.$store.state.threadList;
    }
  },
  template: `
      <section id="thread-list"><ul class="bulleted">
          <li><router-link to="/">Summary</router-link></li>
          <ThreadSummary v-for="thread in threadList" v-bind:thread="thread" v-bind:key="thread.id"></ThreadSummary>
      </ul></section>
  `
};

const ForumSummary = {
  name: 'ForumSummary',
  components: [],
  props: [],
  template: `<section class="main-panel" id="forum-summary">[ForumSummary]</section>`
};

function completeThreadData(vm) {
  if (! vm.$store.state.currentThreadComplete) {
    const number = vm.number;

    // state.currentThread = what we know about this thread from the summary list
    let thread = null;
    const threads = vm.$store.state.threadList.filter(t => t.number == number);
    if ( threads.length > 0 ) {
      thread = threads[0];
      vm.$store.state.currentThread = thread;
    }
    vm.$store.state.currentThreadComplete = false;
    console.log('incomplete thread set')

    // asynchronously update state.currentThread with complete thread data from the server
    axios.get(forum_base_url + number, {
      params: {'data': 'yes'},
      responseType: 'json'
    }).then((response) => {
      const data = response.data;
      vm.$store.state.currentThread = data.thread;
      vm.$store.state.currentThreadComplete = true;
      console.log('complete thread set')
    });
  }
}

const ThreadDisplay = {
  name: 'ThreadDisplay',
  components: [],
  props: ['number'],
  computed: {
    currentThread () {
      return this.$store.state.currentThread;
    }
  },
  watch: {
    number (newVal, oldVal) {
      this.$store.state.currentThreadComplete = false;
    },
  },
  mounted () {
    console.log('ThreadDisplay mounted')
    completeThreadData(this);
    //MathJax.typeset();
  },
  updated () {
    console.log('ThreadDisplay updated')
    completeThreadData(this);
    //MathJax.typeset();
  },
  template: `
      <section class="main-panel" id="current-thread">
          <h2>{{ currentThread.title }}</h2>
          <div v-html="currentThread.html_content"></div>
      </section>
  `
};

const Forum = {
  name: 'Forum',
  props: [],
  computed: {},
  components: {ThreadList},
  template: `
      <ThreadList />
      <router-view></router-view>
  `
};



$(document).ready(() => {
  const store = Vuex.createStore({
    state () {
      return {
        threadList: initial_data.threadList, // lists of threads for summary display/menu
        currentThread: {}, // data for the currently-displayed thread
        currentThreadComplete: false, // is our currentThread data complete (as opposed to the incomplete version from threadList)?
      }
    },
    mutations: {
    },
  });

  const routes = [
    {
      path: '/',
      component: ForumSummary
    },
    {
      path: '/:number',
      component: ThreadDisplay,
      props (route) {
        const number = route.params.number
        return {
          number: number,
        };
      }
    },
  ]

  const router = VueRouter.createRouter({
    history: VueRouter.createWebHistory(forum_base_url),
    routes: routes
  });

  const app = Vue.createApp({
    components: { Forum },
    data () { return {} },
    DISABLED_mounted () {
      axios.get(forum_base_url,{
        params: {'data': 'yes'},
        responseType: 'json'
      }).then((response) => {
        const data = response.data;
        store.state.threadList = data.threadList
      });
    }
  });

  app.use(router);
  app.use(store);
  app.mount(container);
});
