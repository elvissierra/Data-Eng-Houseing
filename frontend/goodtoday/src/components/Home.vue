<template>
  <ion-page>
    <ion-header><ion-toolbar><ion-title>Today</ion-title></ion-toolbar></ion-header>
    <ion-content class="ion-padding">
      <h2>Today has been good, how about you?</h2>
      <ion-segment v-model="mood"><ion-segment-button v-for="n in 5" :value="n">{{n}}</ion-segment-button></ion-segment>
      <ion-segment v-model="energy"><ion-segment-button v-for="n in 5" :value="n">{{n}}</ion-segment-button></ion-segment>
      <ion-button expand="block" @click="saveCheckin">Save Check-in</ion-button>

      <h3 class="ion-margin-top">Pick a path</h3>
      <ion-grid>
        <ion-row>
          <ion-col size="6" v-for="c in cards" :key="c.type">
            <ion-card @click="quickLog(c.type)">
              <ion-card-header><ion-card-title>{{c.label}}</ion-card-title></ion-card-header>
              <ion-card-content>+10 min</ion-card-content>
            </ion-card>
          </ion-col>
        </ion-row>
      </ion-grid>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { upsertCheckin, createActivity, enqueueOp } from '@/services/repo'

const mood = ref(3)
const energy = ref(3)
const cards = [
  { type:'run', label:'Run' },
  { type:'workout', label:'Workout' },
  { type:'brain', label:'Brain Game' },
  { type:'creative', label:'Creative' },
]
function todayISO(){ return new Date().toISOString().slice(0,10) }

async function saveCheckin(){
  await upsertCheckin({ date: todayISO(), mood: mood.value, energy: energy.value })
  await enqueueOp('upsert_checkin', { date: todayISO(), mood: mood.value, energy: energy.value })
}

async function quickLog(type:string){
  const occurred_at = new Date().toISOString()
  await createActivity({ type, minutes: 10, occurred_at })
  await enqueueOp('create_activity', { type, minutes: 10, occurred_at })
}
</script>