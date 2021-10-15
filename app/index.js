var Elm = require('./src/Main.elm');
var ports = require('./ports.js');

var app = Elm.Elm.Main.init({ node: document.getElementById("elm-node") });
ports.init(app);

// leak reference to app for injecting example
window.app = app;
