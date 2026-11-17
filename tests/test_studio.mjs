import test from 'node:test';
import assert from 'node:assert/strict';
import {solve, sceneFromSeed, estimateRGBD, judgePlacement} from '../dist/studio-core.mjs';
test('linear solve handles the IK normal equation',()=>{
 const x=solve([[3,1],[1,2]],[9,8]);assert.ok(Math.abs(x[0]-2)<1e-8);assert.ok(Math.abs(x[1]-3)<1e-8);
});
test('same seed has identical initial scene',()=>assert.deepEqual(sceneFromSeed(10),sceneFromSeed(10)));
test('empty sensor cannot reveal ground truth',()=>assert.equal(estimateRGBD(new Uint8Array(64*64*4),new Float32Array(64*64),64,45,[0,0,1],[1,0,0,0,1,0,0,0,1]),null));
test('placement requires release and valid height',()=>{
 assert.equal(judgePlacement([.48,.24,.393],.08,false),true);
 assert.equal(judgePlacement([.48,.24,.393],.03,false),false);
 assert.equal(judgePlacement([.48,.24,.7],.08,false),false);
 assert.equal(judgePlacement([.48,.24,.393],.08,true),false);
});
