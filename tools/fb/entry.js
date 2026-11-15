import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, onAuthStateChanged } from 'firebase/auth';
import { initializeFirestore, persistentLocalCache, persistentMultipleTabManager, memoryLocalCache, doc, setDoc, onSnapshot } from 'firebase/firestore';
window.FB = { initializeApp, getAuth, signInAnonymously, onAuthStateChanged, initializeFirestore, persistentLocalCache, persistentMultipleTabManager, memoryLocalCache, doc, setDoc, onSnapshot };
