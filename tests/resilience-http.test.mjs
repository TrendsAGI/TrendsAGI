import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchResilience} from '../examples/resilience.mjs';

test('discovers event ID and fetches evidence with server-side API authentication', async () => {
 const calls=[];
 const result=await fetchResilience({apiKey:'test-only',fetchImpl:async (url, options)=>{
  calls.push(url.pathname); assert.equal(options.headers['X-API-Key'],'test-only');
  assert.ok(options.signal);
  return {ok:true,json:async()=> calls.length===1 ? {events:[{id:42}]} : {id:42,source_refs:[]}};
 }});
 assert.deepEqual(calls,['/api/intelligence/crisis-events','/api/intelligence/crisis-events/42/evidence']);
 assert.equal(result.id,42);
});
test('empty event list does not invent an example', async()=>{
 assert.equal(await fetchResilience({apiKey:'test-only',fetchImpl:async()=>({ok:true,json:async()=>({events:[]})})}),null);
});
test('HTTP failure is explicit',async()=>{
 await assert.rejects(fetchResilience({apiKey:'test-only',fetchImpl:async()=>({ok:false,status:403})}),/HTTP 403/);
 await assert.rejects(fetchResilience({apiKey:''}),/required/);
});
