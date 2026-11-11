// Loads the browser scripts into one Node context (they are plain scripts, not modules).
const fs = require('fs'), path = require('path'), vm = require('vm');
module.exports = function load(files) {
  const ctx = { console, Math, Date, JSON, Object, Array, String, Number, Boolean, RegExp, Error, TextEncoder, Uint8Array, Uint32Array, setTimeout };
  vm.createContext(ctx);
  for (const f of files) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'web', 'js', f), 'utf8'), ctx, { filename: f });
  return ctx.WTP;
};
