const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
function setup() {
  let now = 1000, tick;
  const fields = {};
  for (const id of ['power','color','level','state','percent']) fields['#light-'+id] = {value: id==='color'?'#00ff60':'30', checked:false, addEventListener(name,fn){this[name]=fn;}};
  const panel = {querySelector:id=>fields[id]};
  const socket = {readyState:0, addEventListener(_,fn){this.receive=fn;}};
  const sent=[];
  const ctx = {document:{createElement:()=>panel,querySelector:()=>({after(){}})},ws:socket,WebSocket:{OPEN:1},QUERY_CONFIG:11,Date:{now:()=>now},setInterval:fn=>tick=fn,send:(...args)=>{sent.push(args);return true;}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/lights.js'),'utf8'),ctx);
  return {fields,socket,sent,ctx,step(ms=750){now+=ms;tick();},reply(data){socket.receive({target:socket,data:JSON.stringify(data)});}};
}
test('lost initial configuration response is queried again without reconnect',()=>{
  const t=setup();t.step();t.socket.readyState=1;t.step();t.step();
  assert.equal(t.sent.filter(x=>x[0]===11).length,2);
  t.reply({lightReady:true,light:[0,0,0]});
  assert.equal(t.fields['#light-power'].disabled,false);
  t.step();assert.equal(t.sent.length,2);
});
test('lost lamp command retries; stale state cannot cancel latest color',()=>{
  const t=setup();t.socket.readyState=1;t.step();t.reply({lightReady:true,light:[0,0,0]});
  t.fields['#light-power'].checked=true;t.fields['#light-power'].change();
  t.reply({light:[0,0,0]});t.step(500);
  assert.equal(t.sent.filter(x=>x[0]===12).length,2);
  t.reply({light:[0,77,29]});t.step(600);
  assert.equal(t.sent.filter(x=>x[0]===12).length,2);
});
test('disconnect cancels queued command, never turns lamp back on automatically',()=>{
  const t=setup();t.socket.readyState=1;t.step();t.reply({lightReady:true,light:[0,0,0]});
  t.fields['#light-power'].checked=true;t.fields['#light-power'].change();
  t.socket.readyState=3;t.step();t.step();
  assert.equal(t.sent.filter(x=>x[0]===12).length,1);
});
