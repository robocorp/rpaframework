import React from 'react';
import { ThemeProvider, Box, Scroll, Progress } from '@robocorp/ds';
import { Element, Result } from './types';
import { Bridge } from './bridge';
import { Form } from './Form';

const Centered = (props: {
  scrollRef: React.RefObject<HTMLDivElement>;
  children: React.ReactNode;
}) => (
  <ThemeProvider>
    <Box width="100%" height="100%" m={0} p={0}>
      <Scroll variant="custom" ref={props.scrollRef}>
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

export type DialogProps = {
  elements: Element[];
};

export const Dialog = (props: DialogProps): JSX.Element => {
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      const height = scrollRef.current.getBoundingClientRect().height;
      console.log('Height:', height);
      Bridge.setHeight(height);
    }
  }, [props.elements]);

  return (
    <Centered scrollRef={scrollRef}>
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
