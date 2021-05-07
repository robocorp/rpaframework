type Size = 'small' | 'medium' | 'large';

export type Heading = {
  type: 'heading';
  value: string;
  size: Size;
};

export type Text = {
  type: 'text';
  value: string;
  size: Size;
};

export type Link = {
  type: 'link';
  value: string;
  label?: string;
};

export type Image = {
  type: 'image';
  value: string;
  width?: number;
  height?: number;
};

export type File = {
  type: 'file';
  value: string;
  label?: string;
};

export type Icon = {
  type: 'icon';
  variant: 'success' | 'warning' | 'failure';
  size: number;
};

export type TextInput = {
  type: 'input-text';
  name: string;
  label?: string;
  placeholder?: string;
  rows?: number;
};

export type PasswordInput = {
  type: 'input-password';
  name: string;
  label?: string;
  placeholder?: string;
};

export type HiddenInput = {
  type: 'input-hidden';
  name: string;
  value: string;
};

export type FileInput = {
  type: 'input-file';
  name: string;
  label?: string;
  source?: string;
  destination?: string;
  file_type?: string[];
  multiple: boolean;
};

export type DropDown = {
  type: 'input-dropdown';
  name: string;
  options: string[];
  default?: string;
  label?: string;
};

export type RadioButtons = {
  type: 'input-radio';
  name: string;
  options: string[];
  default?: string;
  label?: string;
};

export type Checkbox = {
  type: 'input-checkbox';
  name: string;
  label: string;
  default: boolean;
};

export type Submit = {
  type: 'submit';
  buttons: string[];
  default?: string;
};

export type Element =
  | Heading
  | Text
  | Link
  | Image
  | File
  | Icon
  | TextInput
  | PasswordInput
  | FileInput
  | DropDown
  | RadioButtons
  | Checkbox
  | HiddenInput
  | Submit;

export type Input =
  | TextInput
  | PasswordInput
  | FileInput
  | DropDown
  | RadioButtons
  | Checkbox
  | HiddenInput;

export type Result = { [name: string]: any };

// Type guards

export function isInput(element: Element): element is Input {
  return element.type.startsWith('input-');
}

export function isHidden(element: Element): element is HiddenInput {
  return element.type === 'input-hidden';
}
