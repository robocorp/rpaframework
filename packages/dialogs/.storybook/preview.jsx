import React from "react";
import { ThemeProvider } from "@robocorp/ds";
import { addDecorator } from "@storybook/react";

const themeDecorator = (Story) => (
  <ThemeProvider>
    <Story />
  </ThemeProvider>
);

const viewports = {
  main: {
    name: "Main",
    styles: {
      width: "480px",
      height: "640px",
    },
  },
};

export const decorators = [themeDecorator];

export const parameters = {
  actions: { argTypesRegex: "^on[A-Z].*" },
  viewport: { viewports: viewports, defaultViewport: "main" },
  layout: "fullscreen",
};
