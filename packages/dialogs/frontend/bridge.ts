import { Element, Result } from './types';

interface BridgeWindow extends Window {
  pywebview?: {
    api: {
      getElements: () => Promise<Element[]>;
      setResult: (result: Result) => Promise<void>;
      setHeight: (height: number) => Promise<void>;
      openFile: (path: string) => Promise<void>;
      openFileDialog: (name: string) => Promise<string[]>;
    };
  };
}

declare let window: BridgeWindow;

export const Bridge = {
  async getElements(): Promise<Element[]> {
    if (window.pywebview !== undefined) {
      return await window.pywebview.api.getElements();
    } else {
      return [];
    }
  },

  async setResult(result: Result): Promise<void> {
    if (window.pywebview !== undefined) {
      await window.pywebview.api.setResult(result);
    }
  },

  async setHeight(height: number): Promise<void> {
    if (window.pywebview !== undefined) {
      await window.pywebview.api.setHeight(height);
    }
  },

  async openFile(path: string): Promise<void> {
    if (window.pywebview !== undefined) {
      await window.pywebview.api.openFile(path);
    }
  },

  async openFileDialog(name: string): Promise<string[]> {
    if (window.pywebview !== undefined) {
      return await window.pywebview.api.openFileDialog(name);
    } else {
      return [];
    }
  },
};
