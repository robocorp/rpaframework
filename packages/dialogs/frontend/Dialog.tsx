import React from 'react';
import { ThemeProvider, Box, Scroll, Progress } from '@robocorp/ds';
import { Element, Result } from './types';
import { Bridge } from './bridge';
import { Form } from './Form';

const updateHeight = (scrollRef: React.RefObject<HTMLDivElement>) => {
  const height = Math.max(
    document.body.scrollHeight,
    document.body.offsetHeight,
    document.documentElement.clientHeight,
    document.documentElement.scrollHeight,
    document.documentElement.offsetHeight,
    scrollRef.current ? scrollRef.current.getBoundingClientRect().height : 0,
  );
  console.log('Height:', height);
  Bridge.setHeight(height);
};

const Centered = (props: { children: React.ReactNode }) => {
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    // Calculate height after painting
    const timer = setTimeout(() => updateHeight(scrollRef), 0);
    return () => clearTimeout(timer);
  }, [props.children, scrollRef.current]);

  return (
    <ThemeProvider>
      <Box width="100%" height="100%" m={0} p={0}>
        <Scroll variant="custom" ref={scrollRef}>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="center"
            minHeight="100%"
          >
            {props.children}
          </Box>
        </Scroll>
      </Box>
    </ThemeProvider>
  );
};

export type DialogProps = {
  elements: Element[];
};

export const Dialog = (props: DialogProps): JSX.Element => {
  return (
    <Centered>
      {props.elements.length === 0 ? (
        <Box height={48} width={48}>
          <Progress variant="circular" />
        </Box>
      ) : (
        <Box width="100%" p={32}>
          <Form
            elements={props.elements}
            onSubmit={(result: Result) => {
              console.log('Result:', result);
              Bridge.setResult(result);
            }}
          />
        </Box>
      )}
    </Centered>
  );
};
