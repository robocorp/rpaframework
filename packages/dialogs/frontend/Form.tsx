import React from 'react';
import { Box } from '@robocorp/ds';

import {
  Heading,
  Text,
  Link,
  Image,
  File,
  Icon,
  TextInput,
  PasswordInput,
  FileInput,
  DropDown,
  RadioButtons,
  Checkbox,
  Submit,
} from './Elements';
import * as Types from './types';

function unreachable(x: never): never {
  throw new Error(`Unexpected value: ${x}`);
}

const toComponent = (
  element: Types.Element,
  result: Types.Result,
  setResult: React.Dispatch<React.SetStateAction<Types.Result>>,
  onSubmit: (value: string) => void,
): JSX.Element | null => {
  const inputProps = {
    value: Types.isInput(element) && result[element.name],
    setValue: (value: any) => {
      if (Types.isInput(element)) {
        setResult((previous: Types.Result) => ({
          ...previous,
          [element.name]: value,
        }));
      }
    },
  };

  switch (element.type) {
    case 'heading':
      return <Heading element={element} />;
    case 'text':
      return <Text element={element} />;
    case 'link':
      return <Link element={element} />;
    case 'image':
      return <Image element={element} />;
    case 'file':
      return <File element={element} />;
    case 'icon':
      return <Icon element={element} />;
    case 'input-text':
      return <TextInput element={element} {...inputProps} />;
    case 'input-password':
      return <PasswordInput element={element} {...inputProps} />;
    case 'input-file':
      return <FileInput element={element} />;
    case 'input-dropdown':
      return <DropDown element={element} {...inputProps} />;
    case 'input-radio':
      return <RadioButtons element={element} {...inputProps} />;
    case 'input-checkbox':
      return <Checkbox element={element} {...inputProps} />;
    case 'input-hidden':
      return null; // No need to create DOM element
    case 'submit':
      return <Submit element={element} onSubmit={onSubmit} />;
    default:
      return unreachable(element);
  }
};

const getDefault = (element: Types.Input) => {
  if (Types.isHidden(element)) {
    return element.value;
  } else if ('default' in element) {
    return element.default !== undefined ? element.default : '';
  } else {
    return '';
  }
};

export const Form = (props: {
  elements: Types.Element[];
  onSubmit: (result: Types.Result) => void;
}): JSX.Element => {
  const [result, setResult] = React.useState<Types.Result>(
    props.elements.reduce((state, element) => {
      if (Types.isInput(element)) {
        state[element.name] = getDefault(element);
      }
      return state;
    }, {} as Types.Result),
  );

  const onSubmit = (value: string) => {
    props.onSubmit({ ...result, submit: value });
  };

  const components: JSX.Element[] = props.elements
    .map((element) => toComponent(element, result, setResult, onSubmit))
    .filter((component) => component !== null)
    .map((component, index) => (
      <Box
        key={index}
        mt={index !== 0 ? '20px' : '0'}
        textAlign="initial"
        width="100%"
      >
        {component}
      </Box>
    ));

  return (
    <Box display="flex" flexDirection="column">
      {components}
    </Box>
  );
};
