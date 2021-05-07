import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Dialog } from './Dialog';
import { Element } from './types';
import { Bridge } from './bridge';

export class App {
  private elements: Element[];

  constructor() {
    this.elements = [];
    this.onReady = this.onReady.bind(this);
    window.addEventListener('pywebviewready', this.onReady);
  }

  private onReady(): void {
    Bridge.getElements().then((elements) => {
      window.removeEventListener('pywebviewready', this.onReady);
      this.elements = elements;
      this.render();
    });
  }

  private render(): void {
    const props = {
      elements: this.elements,
    };

    ReactDOM.render(
      React.createElement(Dialog, props),
      document.getElementById('app'),
    );
  }
}

new App();
