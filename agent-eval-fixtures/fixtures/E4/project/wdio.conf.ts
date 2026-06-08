import type { Options } from "@wdio/types";
import { config as dotenvConfig } from "dotenv";

// Load environment variables from .env file
dotenvConfig({ path: "./.env", override: true });

// Explicitly set the env vars to ensure they're available
process.env.SUPATEST_API_URL =
  process.env.SUPATEST_API_URL || "http://localhost:9090";
process.env.SUPATEST_API_KEY =
  process.env.SUPATEST_API_KEY || "sk_test_benchmark_dummy";
process.env.SUPATEST_PROJECT_ID =
  process.env.SUPATEST_PROJECT_ID || "proj_local_swaglabs";

export const config: Options.Testrunner = {
  // ====================
  // Runner Configuration
  // ====================
  runner: "local",

  // ==================
  // Specify Test Files
  // ==================
  specs: ["./test/specs/**/*.ts"],

  // ============
  // Capabilities
  // ============
  // Define your capabilities here. WebdriverIO can run multiple capabilities at the same
  // time. Depending on the number of capabilities, WebdriverIO launches several test
  // sessions. Within your capabilities you can overwrite the specified values and options.
  maxInstances: 10,
  capabilities: [
    {
      browserName: "chrome",
      browserVersion: "latest",
      "wdio:chromedriverOptions": {
        // For more options see https://github.com/chromium/chromium/tree/master/chrome/test/chromedriver/json#chrome-capabilities
      },
      // Disable headless mode by default, can be overridden with --headed flag
      "goog:chromeOptions": {
        args:
          process.env.HEADED === "true"
            ? []
            : [
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
              ],
      },
    },
  ],

  // ===================
  // Test Configurations
  // ===================
  // Level of logging verbosity: trace | debug | info | warn | error | silent
  logLevel: "info",

  // Set specific log levels per logger
  logLevels: {
    webdriver: "info",
    "@wdio/applitools-service": "info",
  },

  // Warns when a deprecated command is used
  // deprecationWarnings: true,

  // If you only want to run your tests until a specific amount of tests have failed use
  // bail (default is 0 - don't bail, run all tests).
  bail: 0,

  // Set a base URL in order to shorten url command calls. If your `url` parameter starts
  // with `/`, the base url gets prepended, not including the path portion of your baseUrl.
  // If your `url` parameter does not start with `/` and is a completely valid URL,
  // the base url will not be prepended.
  baseUrl: "https://www.saucedemo.com",

  // Default timeout for all waitFor* commands.
  waitforTimeout: 10000,

  // Default timeout in milliseconds for request
  // if browser driver or grid doesn't send response
  connectionRetryTimeout: 120000,

  // Default request retries count
  connectionRetryCount: 3,

  // Test runner services
  // Services take over a specific job you don't want to take care of. They enhance
  // your test setup with almost no effort. Unlike plugins, they don't add new
  // commands. Instead, they hook themselves up into the test process.
  services: [],

  // Framework you want to run your specs with.
  // The following are supported: Mocha, Jasmine, and Cucumber
  // see also: https://webdriver.io/docs/frameworks
  framework: "mocha",

  // The number of times to retry the entire specfile when it fails as a whole
  specFileRetries: 0,
  // Delay in seconds between the spec file retry attempts
  specFileRetriesDelay: 0,
  // Whether or not retried spec files should be retried immediately or deferred to the end of the queue
  specFileRetriesDeferred: false,

  // Test reporter for stdout.
  // The following are supported: dot (default), spec, json, junit, ...
  // see also: https://webdriver.io/docs/configuration#reporters
  reporters: [
    "spec",
    [
      "@supatest/webdriverio-reporter",
      {
        projectId: "proj_local_swaglabs",
        apiKey: "sk_test_benchmark_dummy",
        apiUrl: "http://localhost:9090",
      },
    ],
  ],

  // Options
  // =======
  mochaOpts: {
    ui: "bdd",
    timeout: 60000,
  },

  // ==================
  // Hooks
  // ==================
  // WebdriverIO provides several hooks you can use to interfere with the test process in order to enhance
  // it and to build services around it. You can either apply a single function or an array of
  // methods to it. If one of them returns with a promise, WebdriverIO will wait until that promise got
  // resolved to continue.
  /**
   * Gets executed once before all workers get launched.
   * @param {Object} config wdio configuration object
   * @param {Array.<Object>} capabilities list of capabilities details
   */
  // onPrepare: function(config, capabilities) {
  // },
  /**
   * Gets executed before a worker process is spawned and can be used to initialise specific service
   * for that worker as well as modified runtime environment of worker.
   * @param  {String} cid      capability id (e.g 0-0)
   * @param  {[type]} caps     object containing capabilities for session that will be spawn in the worker
   * @param  {[type]} specs    specs to be run in the worker process
   * @param  {[type]} args     object that will be merged with the main configuration once worker is initialised
   * @param  {[type]} execArgv list of string arguments passed to the worker process
   */
  // onWorkerStart: function(cid, caps, specs, args, execArgv) {
  // },
  /**
   * Gets executed just after a worker process has exited.
   * @param  {String} cid      capability id (e.g 0-0)
   * @param  {[type]} caps     object containing capability details
   * @param  {[type]} specs    specs to be run in the worker process
   * @param  {[type]} exit     0 - success, 1 - fail
   * @param  {[type]} retries  number of retries used
   */
  // onWorkerEnd: function(cid, caps, specs, exit, retries) {
  // },
  /**
   * Gets executed just before initialising the webdriver session and test framework.
   * @param {Object} config wdio configuration object
   * @param {Array.<Object>} capabilities list of capabilities details
   * @param {Array.<String>} specs List of spec file paths that are to be run
   * @param {String} cid worker id (e.g. 0-0)
   */
  // beforeSession: function(config, capabilities, specs, cid) {
  // },
  /**
   * Gets executed before test execution begins. At this point you can access all global
   * variables, such as `browser`. It is the perfect place to define custom commands.
   * @param {Object} config wdio configuration object
   * @param {Array.<Object>} capabilities list of capabilities details
   * @param {Array.<String>} specs List of spec file paths that are to be run
   */
  // before: function(config, capabilities, specs) {
  // },
  /**
   * Runs before a WebdriverIO command gets executed.
   * @param {String} commandName hook command name
   * @param {Array} args arguments that command would receive
   */
  // beforeCommand: function(commandName, args) {
  // },
  /**
   * Hook that gets executed before the suite starts
   * @param {Object} suite suite details
   */
  // beforeSuite: function(suite) {
  // },
  /**
   * Hook that gets executed _before_ a hook within the suite starts (e.g. runs before calling
   * beforeEach in Mocha)
   */
  // beforeHook: function(test, context, hookName) {
  // },
  /**
   * Hook that gets executed _after_ a hook within the suite finishes (e.g. runs after calling
   * afterEach in Mocha)
   */
  // afterHook: function(test, context, { error, result, duration, passed, retries }, hookName) {
  // },
  /**
   * Function to be executed before a test (in Mocha/Jasmine) or a step (in Cucumber) starts.
   * @param {Object} test test details
   */
  // beforeTest: function(test) {
  // },
  /**
   * Runs before a WebdriverIO command gets executed.
   * @param {String} commandName hook command name
   * @param {Array} args arguments that command would receive
   */
  // beforeCommand: function(commandName, args) {
  // },
  /**
   * Hook that gets executed after the suite has ended
   * @param {Object} suite suite details
   */
  // afterSuite: function(suite) {
  // },
  /**
   * Runs after a WebdriverIO command gets executed
   * @param {String} commandName hook command name
   * @param {Array} args arguments that command would receive
   * @param {Number} result 0 - command success, 1 - command error
   * @param {Object} error error object if any
   */
  // afterCommand: function(commandName, args, result, error) {
  // },
  /**
   * Gets executed after all tests are done. You still have access to all global variables from
   * the test.
   * @param {Number} result 0 - test pass, 1 - test fail
   * @param {Array.<Object>} capabilities list of capabilities details
   * @param {Array.<String>} specs List of spec file paths that ran
   */
  // after: function(result, capabilities, specs) {
  // },
  /**
   * Gets executed right after terminating the webdriver session.
   * @param {Object} config wdio configuration object
   * @param {Array.<Object>} capabilities list of capabilities details
   * @param {Array.<String>} specs List of spec file paths that ran
   * @param {Number} exit 0 - success, 1 - fail
   */
  // afterSession: function(config, capabilities, specs, exit) {
  // },
  /**
   * Gets executed after all workers got shut down and the process is about to exit.
   * An error thrown in the onComplete hook will result in the test run failing.
   * @param {Object} exitCode 0 - success, 1 - fail
   * @param {Object} config wdio configuration object
   * @param {Array.<Object>} capabilities list of capabilities details
   * @param {<Object>} results object containing test results
   */
  // onComplete: function(exitCode, config, capabilities, results) {
  // },
  /**
   * Gets executed when a refresh to the WebDriver session happens, for example when a new
   * test starts in Mocha.
   * @param {String} oldSessionId session ID of the old session
   * @param {String} newSessionId session ID of the new session
   */
  // onReload: function(oldSessionId, newSessionId) {
  // }
};
