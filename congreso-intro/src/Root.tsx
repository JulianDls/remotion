import React from 'react';
import {Composition} from 'remotion';
import {FigureTest} from './dev/FigureTest';
import {FPS, H, TOTAL_FRAMES, W} from './config';
import {Intro} from './Intro';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition id="Intro" component={Intro} durationInFrames={TOTAL_FRAMES} fps={FPS} width={W} height={H} />
			<Composition id="FigureTest" component={FigureTest} durationInFrames={60} fps={FPS} width={1920} height={1080} />
		</>
	);
};
