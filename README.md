# KubeWhisper: Talk to your Kubernetes cluster like a friend

![KubeWhisper Cover](cover.jpg)

[![GitHub Actions Status](https://img.shields.io/github/actions/workflow/status/PatrickKalkman/kube-whisper/ci.yml?branch=master)](https://github.com/PatrickKalkman/kube-whisper/actions)
[![GitHub stars](https://img.shields.io/github/stars/PatrickKalkman/kube-whisper)](https://github.com/PatrickKalkman/kube-whisper/stargazers)
[![GitHub contributors](https://img.shields.io/github/contributors/PatrickKalkman/kube-whisper)](https://github.com/PatrickKalkman/kube-whisper/graphs/contributors)
[![GitHub last commit](https://img.shields.io/github/last-commit/PatrickKalkman/kube-whisper)](https://github.com/PatrickKalkman/kube-whisper)
[![open issues](https://img.shields.io/github/issues/PatrickKalkman/kube-whisper)](https://github.com/PatrickKalkman/kube-whisper/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://makeapullrequest.com)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)

Ever wished you could just ask your Kubernetes cluster what's going on? No more wrestling with complex kubectl commands or digging through documentation. KubeWhisper lets you manage your cluster through natural conversation, powered by OpenAI's Realtime API. Just speak, and let KubeWhisper handle the rest.

Read the full story behind KubeWhisper in my [Medium article](https://medium.com/@pkalkman).

## ✨ Key Features

- **Natural Voice Control**: Talk to your cluster like you're chatting with a colleague
- **Smart Command Translation**: Automatically converts your voice to the right kubectl commands
- **Real-time Responses**: Get instant audio feedback about your cluster's state
- **Full K8s Integration**: Access all the key Kubernetes operations through voice
- **Secure by Design**: Uses your existing kubectl credentials and permissions
- **Clean Voice Interface**: Clear, concise responses that get to the point

## 🚀 Getting Started

KubeWhisper uses UV for seamless Python package management. Here's how to get chatting with your cluster in minutes:

### Prerequisites

- Python 3.12 or higher
- A configured Kubernetes cluster
- OpenAI API key
- A working microphone

### Installation

1. **Install UV** (if you haven't already):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Clone KubeWhisper**:
```bash
git clone https://github.com/YourUsername/kubewhisper
cd kubewhisper
```

3. **Set up your OpenAI key**:
```bash
echo "OPENAI_API_KEY=your-key-goes-here" > .env
```

### Running KubeWhisper

Ready to talk to your cluster? It's as simple as:

```bash
uv run kubewhisper
```

Want more details about what's happening? Add the verbose flag:

```bash
uv run kubewhisper --verbose
```

## 🎯 Example Commands

Here's what you can say to KubeWhisper:

- "How many pods are running?"
- "What's the status of my cluster?"
- "Show me the latest events"
- "Get the version of Kubernetes"
- "Switch to the production cluster"

## 📚 How It Works

KubeWhisper turns your voice commands into cluster actions in four quick steps:

1. **Voice Input**: Captures your command through the microphone
2. **AI Processing**: Uses OpenAI's Realtime API to understand your intent
3. **Kubernetes Action**: Executes the appropriate cluster command
4. **Voice Response**: Returns the results as natural speech

## 💰 Cost Considerations

A quick heads-up: Since we're using OpenAI's Realtime API, there are some costs involved.

## 🤝 Contributing

Got ideas to make KubeWhisper even better? I'd love your help! Here's how:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Check out our [Contributing Guide](CONTRIBUTING.md) for more details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

KubeWhisper wouldn't be possible without:

- OpenAI's Realtime API for voice processing
- The Kubernetes Python client
- UV for elegant package management
- PyAudio for voice input/output
- The amazing open-source community

## 🌟 What's Next?

Exciting things are coming to KubeWhisper:
- Local AI support for offline operation
- More Kubernetes command coverage
- Multi-language support
- Cost optimization features

Want to help shape the future of KubeWhisper? Star the repo, open an issue, or submit a PR. Let's make Kubernetes management as easy as having a conversation! 🚀