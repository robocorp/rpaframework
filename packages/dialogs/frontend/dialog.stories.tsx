import React from 'react';
import { Story, Meta } from '@storybook/react';
import { Dialog, DialogProps } from './Dialog';

const imageUrl = [
  'https://cdn.robocorp.com/brand/Logo/',
  'Negative%20logo%20transparent%20with%20buffer%20space/',
  'Negative%20logo%20transparent%20with%20buffer%20space.svg',
].join('');

export default {
  title: 'Dialog',
  component: Dialog,
} as Meta;

const Template: Story<DialogProps> = (args) => <Dialog {...args} />;

export const All = Template.bind({});
All.args = {
  elements: [
    {
      type: 'heading',
      value: 'Large Title',
      size: 'large',
    },
    {
      type: 'heading',
      value: 'Medium Title',
      size: 'medium',
    },
    {
      type: 'heading',
      value: 'Small Title',
      size: 'small',
    },
    {
      type: 'text',
      value: 'Some text in large size',
      size: 'large',
    },
    {
      type: 'text',
      value: 'Some text in medium size',
      size: 'medium',
    },
    {
      type: 'text',
      value: 'Some text in small size',
      size: 'small',
    },
    {
      type: 'link',
      value: 'https://robocorp.com',
    },
    {
      type: 'link',
      value: 'https://robocorp.com',
      label: 'Robocorp Site',
    },
    {
      type: 'image',
      value: imageUrl,
    },
    {
      type: 'image',
      value: imageUrl,
      width: 180,
    },
    {
      type: 'file',
      value: 'C:\\Example\\Orders.xlsx',
    },
    {
      type: 'file',
      value: 'C:\\Example\\Orders.xlsx',
      label: 'Results',
    },
    {
      type: 'icon',
      variant: 'success',
      size: 32,
    },
    {
      type: 'icon',
      variant: 'warning',
      size: 32,
    },
    {
      type: 'icon',
      variant: 'failure',
      size: 32,
    },
    {
      type: 'input-text',
      name: 'text-1',
    },
    {
      type: 'input-text',
      name: 'text-2',
      label: 'Text',
      placeholder: 'Some text here',
    },

    {
      type: 'input-text',
      name: 'text-3',
      label: 'Text',
      placeholder: 'Some text here',
      rows: 3,
    },
    {
      type: 'input-password',
      name: 'password-1',
    },
    {
      type: 'input-password',
      name: 'password-2',
      label: 'Password',
      placeholder: 'A password here',
    },
    {
      type: 'input-hidden',
      name: 'hidden-1',
      value: "Some value you shouldn't see",
    },
    {
      type: 'input-file',
      name: 'file-1',
      multiple: false,
    },
    {
      type: 'input-file',
      name: 'file-2',
      label: 'Input file',
      multiple: false,
    },
    {
      type: 'input-dropdown',
      name: 'dropdown-1',
      options: ['First', 'Second', 'Third'],
    },
    {
      type: 'input-dropdown',
      name: 'dropdown-2',
      options: ['First', 'Second', 'Third'],
      default: 'Second',
      label: 'Drop-down',
    },
    {
      type: 'input-radio',
      name: 'radio-1',
      options: ['First', 'Second', 'Third'],
    },
    {
      type: 'input-radio',
      name: 'radio-2',
      options: ['First', 'Second', 'Third'],
      default: 'Second',
      label: 'Radio buttons',
    },
    {
      type: 'input-checkbox',
      name: 'checkbox-1',
      label: 'Checked',
      default: true,
    },
    {
      type: 'input-checkbox',
      name: 'checkbox-2',
      label: 'Unchecked',
      default: false,
    },
    {
      type: 'submit',
      buttons: ['Left', 'Right'],
    },
    {
      type: 'submit',
      buttons: ['Cancel', 'Submit'],
      default: 'Submit',
    },
  ],
};

export const FileResults = Template.bind({});
FileResults.args = {
  elements: [
    {
      type: 'icon',
      variant: 'success',
      size: 48,
    },
    {
      type: 'heading',
      value: 'Results',
      size: 'large',
    },
    {
      type: 'file',
      value: 'C:\\Output\\Orders.xlsx',
    },
    {
      type: 'file',
      value: 'C:\\Output\\Customers.xlsx',
    },
    {
      type: 'file',
      value: 'C:\\Output\\Report.pdf',
    },
    {
      type: 'submit',
      buttons: ['Close'],
    },
  ],
};

export const ErrorMessage = Template.bind({});
ErrorMessage.args = {
  elements: [
    {
      type: 'icon',
      variant: 'failure',
      size: 48,
    },
    {
      type: 'heading',
      value: 'Assistant failed',
      size: 'large',
    },
    {
      type: 'text',
      value: [
        'The assistant failed because of some reason ',
        'outside your control. Please contant the ',
        'support at support@company.com.',
      ].join(''),
      size: 'medium',
    },
    {
      type: 'submit',
      buttons: ['Close'],
    },
  ],
};

export const LargeImage = Template.bind({});
LargeImage.args = {
  elements: [
    {
      type: 'image',
      value: imageUrl,
      width: 800,
    },
  ],
};

export const NoElements = Template.bind({});
NoElements.args = {
  elements: [],
};
