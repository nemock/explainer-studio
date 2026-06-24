import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// M3 / 16 GB unified memory — keep the headless-Chrome fleet modest (PRD memory budget)
Config.setConcurrency(2);
