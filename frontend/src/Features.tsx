import { FileText } from 'lucide-react';
import { Empty, PageHeading } from './App';
import { type Job } from './api';
export function FeatureSlot({name,job}:{name:string;job:Job|null;notify:(s:string)=>void}){return <><PageHeading title={name} subtitle={job?`${job.title} · ${job.company}`:'Your search, thoughtfully organized.'}/><Empty icon={<FileText size={28}/>} title={`Your ${name.toLowerCase()} starts here`} text="Your workspace is ready for the next step."/></>;}
