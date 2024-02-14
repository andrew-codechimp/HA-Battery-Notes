import { formatTimeWithSeconds } from "custom-card-helpers";
import {
  HassEntity,
  HassEntityAttributeBase,
} from "home-assistant-js-websocket";
import { textSpanIsEmpty } from "typescript";

export interface Dictionary<TValue> {
  [id: string]: TValue;
}

/*export interface AlarmEntity extends HassEntity {
  attributes: HassEntityAttributeBase & {
    code_format: 'number' | 'text';
    code_arm_required: boolean;
    code_disarm_required: boolean;
    disarm_after_trigger: boolean;
    supported_features: number;
    sensors: Dictionary<number>;
    delays: Dictionary<number>;
    users: Dictionary<number>;
    config: number;
    push_target?: string;
    siren_entity?: string;
  };
}*/

export class SmartIrrigationConfig {
  calctime: string;
  use_owm: boolean;
  units: string;
  autocalcenabled: boolean;
  autoupdateenabled: boolean;
  autoupdateschedule: string;
  autoupdatedelay: number;
  autoupdateinterval: number;
  cleardatatime: string;
  autoclearenabled: boolean;

  constructor() {
    this.calctime = "23:00";
    this.use_owm = false;
    this.units = "";
    this.autocalcenabled = true;
    this.autoupdateenabled = true;
    this.autoupdateschedule = "";
    this.autoupdatedelay = 0;
    this.autoupdateinterval = 0;
    this.autoclearenabled = true;
    this.cleardatatime = "23:59";
  }
}

export enum SmartIrrigationZoneState {
  Disabled = "disabled",
  Manual = "manual",
  Automatic = "automatic",
}

//export type SmartIrrigationZone = {
export class SmartIrrigationZone {
  id: number;
  name: string;
  size: number;
  throughput: number;
  state: SmartIrrigationZoneState;
  duration: number;
  module?: number;
  bucket: number;
  delta: number;
  old_bucket: number;
  explanation: string;
  multiplier: number;
  mapping?: number;
  lead_time: number;
  maximum_duration?: number;
  maximum_bucket?: number;
  last_calculated?: Date;

  constructor(
    i: number,
    n: string,
    s: number,
    t: number,
    st: SmartIrrigationZoneState,
    d: number
  ) {
    this.id = i;
    this.name = n;
    this.size = s;
    this.throughput = t;
    this.state = st;
    this.duration = d;
    this.module = undefined;
    this.bucket = 0;
    this.delta = 0;
    this.old_bucket = 0;
    this.explanation = "";
    this.multiplier = 1.0;
    this.mapping = undefined;
    this.lead_time = 0;
    this.maximum_duration = 3600; //default maximum duration to one hour = 3600 seconds
    this.maximum_bucket = 50; //default maximum bucket size to 50 mm
    this.last_calculated = undefined;
  }
}

export class SmartIrrigationModule {
  id: number;
  name: string;
  description: string;
  //duration: number;
  config: object;
  schema: object;
  constructor(i: number, n: string, d: string, c: object, s: object) {
    this.id = i;
    this.name = n;
    this.description = d;
    this.config = c;
    this.schema = s;
    //this.duration = dr;
    //this.module = m;
  }
}

export class SmartIrrigationMapping {
  id: number;
  name: string;
  mappings: object;
  data_last_updated?: Date;

  constructor(i: number, n: string, m: object) {
    this.id = i;
    this.name = n;
    this.mappings = m;
    this.data_last_updated = undefined;
  }
}
