import React from 'react';
import {
  Grid,
  Box,
  Button,
  Input,
  Select,
  RadioGroup,
  Radio,
  Checkbox as CheckboxComponent,
  Link as LinkComponent,
  H2,
  H3,
  H4,
  P,
} from '@robocorp/ds';
import {
  IconExternalLink,
  IconFile,
  IconCheck,
  IconExclamationTriangle,
  IconX,
} from '@robocorp/ds/icons';

import * as Types from './types';
import { Bridge } from './bridge';

function unreachable(x: never): never {
  throw new Error(`Unexpected value: ${x}`);
}

const baseName = (path: string) => path.replace(/^.*[\\/]/, '');

const Centered = (props: { children: React.ReactNode }) => (
  <Box textAlign="center">{props.children}</Box>
);

export const Heading = (props: { element: Types.Heading }): JSX.Element => {
  let heading: JSX.Element;
  switch (props.element.size) {
    case 'small':
      heading = <H4>{props.element.value}</H4>;
      break;
    case 'medium':
      heading = <H3>{props.element.value}</H3>;
      break;
    case 'large':
      heading = <H2>{props.element.value}</H2>;
      break;
    default:
      unreachable(props.element.size);
  }
  return <Centered>{heading}</Centered>;
};

export const Text = (props: { element: Types.Text }): JSX.Element => {
  switch (props.element.size) {
    case 'small':
      return <P fontSize="12px">{props.element.value}</P>;
    case 'medium':
      return <P fontSize="14px">{props.element.value}</P>;
    case 'large':
      return <P fontSize="18px">{props.element.value}</P>;
    default:
      unreachable(props.element.size);
  }
};

export const Link = (props: { element: Types.Link }): JSX.Element => (
  <LinkComponent
    icon={IconExternalLink}
    target="_blank"
    href={
      !/^(?:f|ht)tps?:\/\//.test(props.element.value)
        ? `http://${props.element.value}`
        : props.element.value
    }
  >
    {props.element.label ?? props.element.value}
  </LinkComponent>
);

export const Image = (props: { element: Types.Image }): JSX.Element => {
  const style: React.CSSProperties = { height: props.element.height };

  if (props.element.width) {
    style.width = props.element.width;
  } else {
    style.maxWidth = '100%';
  }

  return (
    <Centered>
      <img src={props.element.value} style={style} />
    </Centered>
  );
};

export const File = (props: { element: Types.File }): JSX.Element => (
  <Centered>
    <Button
      variant="dark"
      icon={IconFile}
      onClick={() => {
        Bridge.openFile(props.element.value);
      }}
    >
      {props.element.label ?? baseName(props.element.value)}
    </Button>
  </Centered>
);

export const Icon = (props: { element: Types.Icon }): JSX.Element => {
  const { size, variant } = props.element;
  let icon: JSX.Element;
  switch (variant) {
    case 'success':
      icon = <IconCheck size={size} color="green50" />;
      break;
    case 'warning':
      icon = <IconExclamationTriangle size={size} color="yellow30" />;
      break;
    case 'failure':
      icon = <IconX size={size} color="red50" />;
      break;
    default:
      unreachable(variant);
  }
  return <Centered>{icon}</Centered>;
};

export const TextInput = (props: {
  element: Types.TextInput;
  value: string;
  setValue: (value: string) => void;
}): JSX.Element => (
  <Input
    id={props.element.name}
    label={props.element.label}
    placeholder={props.element.placeholder}
    rows={props.element.rows}
    value={props.value}
    onChange={(e) => {
      props.setValue(e.target.value);
    }}
  />
);

export const PasswordInput = (props: {
  element: Types.PasswordInput;
  value: string;
  setValue: (value: string) => void;
}): JSX.Element => (
  <Input
    type="secret"
    id={props.element.name}
    label={props.element.label}
    placeholder={props.element.placeholder}
    value={props.value}
    onChange={(e) => {
      props.setValue(e.target.value);
    }}
  />
);

export const FileInput = (props: { element: Types.FileInput }): JSX.Element => {
  const [files, setFiles] = React.useState<string[]>([]);

  let text: string;
  switch (files.length) {
    case 0:
      text = 'No file selected';
      break;
    case 1:
      text = baseName(files[0]);
      break;
    default:
      text = `${files.length} files selected`;
      break;
  }

  return (
    <>
      <P mb={8}>{props.element.label}</P>
      <Grid flexDirection="row" alignItems="center">
        <Button
          variant="dark"
          icon={IconFile}
          onClick={async () => {
            const result = await Bridge.openFileDialog(props.element.name);
            setFiles(result);
          }}
        >
          Browse…
        </Button>
        <P ml={16}>{text}</P>
      </Grid>
    </>
  );
};

export const DropDown = (props: {
  element: Types.DropDown;
  value: string;
  setValue: (value: string) => void;
}): JSX.Element => (
  <Select
    id={props.element.name}
    items={props.element.options.map((opt) => ({ label: opt, value: opt }))}
    label={props.element.label}
    value={props.value}
    onChange={props.setValue}
  />
);

export const RadioButtons = (props: {
  element: Types.RadioButtons;
  value: string;
  setValue: (value: string) => void;
}): JSX.Element => (
  <RadioGroup id={props.element.name} direction="column" value={props.value}>
    {props.element.options.map((opt) => (
      <Radio label={opt} value={opt} key={opt} onChange={props.setValue} />
    ))}
  </RadioGroup>
);

export const Checkbox = (props: {
  element: Types.Checkbox;
  value: boolean;
  setValue: (value: boolean) => void;
}): JSX.Element => (
  <CheckboxComponent
    id={props.element.name}
    label={props.element.label}
    checked={props.value}
    onChange={(e) => props.setValue(e.target.checked)}
  />
);

export const Submit = (props: {
  element: Types.Submit;
  onSubmit: (value: string) => void;
}): JSX.Element => (
  <Grid
    flexDirection="row"
    alignItems="center"
    justifyContent="center"
    width="100%"
    mt={16}
  >
    {props.element.buttons.map((opt, index) => (
      <Box ml={index !== 0 ? 16 : 0} key={opt}>
        <Button
          id={opt}
          type="submit"
          variant={opt === props.element.default ? 'primary' : 'secondary'}
          onClick={() => props.onSubmit(opt)}
        >
          {opt}
        </Button>
      </Box>
    ))}
  </Grid>
);
