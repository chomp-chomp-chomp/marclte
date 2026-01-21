import SwiftUI

struct ContentView: View {
    @State private var inputURL: URL?
    @State private var mergeURLs: [URL] = []
    @State private var outputURL: URL?
    @State private var outputDirectory: URL?
    @State private var selectedOperation: Operation = .count
    @State private var splitEvery: String = "500"
    @State private var outputFormat: MarcFormat = .mrc
    @State private var isRunning = false
    @State private var logs: [String] = []
    @State private var progressText: String = ""
    @State private var detectedFormat: String = "Unknown"

    private let runner = MarcliteRunner()

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            GroupBox(label: Text("Input")) {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Button("Choose file…") { selectInputFile() }
                        Text(inputURL?.lastPathComponent ?? "No file selected")
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                    Text("Detected format: \(detectedFormat)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            GroupBox(label: Text("Operation")) {
                VStack(alignment: .leading, spacing: 12) {
                    Picker("Operation", selection: $selectedOperation) {
                        ForEach(Operation.allCases) { operation in
                            Text(operation.title).tag(operation)
                        }
                    }
                    .pickerStyle(.segmented)

                    if selectedOperation == .split {
                        HStack {
                            Text("Records per file")
                            TextField("500", text: $splitEvery)
                                .frame(width: 80)
                                .textFieldStyle(.roundedBorder)
                        }
                    }

                    if selectedOperation == .merge {
                        VStack(alignment: .leading, spacing: 4) {
                            Button("Select files…") { selectMergeFiles() }
                            Text(mergeURLs.isEmpty ? "No merge files selected" : "\(mergeURLs.count) file(s) selected")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    if selectedOperation == .merge || selectedOperation == .convert {
                        Picker("Output format", selection: $outputFormat) {
                            ForEach(MarcFormat.allCases) { format in
                                Text(format.displayName).tag(format)
                            }
                        }
                        .frame(maxWidth: 220)
                    }
                }
            }

            GroupBox(label: Text("Output")) {
                VStack(alignment: .leading, spacing: 8) {
                    if selectedOperation == .split {
                        HStack {
                            Button("Choose folder…") { selectOutputFolder() }
                            Text(outputDirectory?.path ?? "No folder selected")
                                .lineLimit(1)
                                .truncationMode(.middle)
                        }
                    } else if selectedOperation == .merge || selectedOperation == .convert {
                        HStack {
                            Button("Choose file…") { selectOutputFile() }
                            Text(outputURL?.path ?? "No file selected")
                                .lineLimit(1)
                                .truncationMode(.middle)
                        }
                    } else {
                        Text("No output location required for count.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            HStack {
                Button("Run") { runOperation() }
                    .disabled(!canRun || isRunning)
                if isRunning {
                    ProgressView()
                    Text(progressText)
                        .font(.caption)
                }
            }

            GroupBox(label: Text("Log")) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(logs.indices, id: \.self) { index in
                            Text(logs[index])
                                .font(.system(.caption, design: .monospaced))
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(minHeight: 160)
            }
        }
        .padding()
        .frame(minWidth: 680, minHeight: 520)
        .onChange(of: inputURL) { newValue in
            detectedFormat = FormatDetector.detect(url: newValue) ?? "Unknown"
        }
    }

    private var canRun: Bool {
        switch selectedOperation {
        case .count:
            return inputURL != nil
        case .split:
            return inputURL != nil && outputDirectory != nil && Int(splitEvery) != nil
        case .merge:
            return !mergeURLs.isEmpty && outputURL != nil
        case .convert:
            return inputURL != nil && outputURL != nil
        }
    }

    private func runOperation() {
        guard canRun else { return }
        logs.removeAll()
        progressText = ""
        isRunning = true

        let request = MarcliteRequest(
            operation: selectedOperation,
            inputURL: inputURL,
            mergeURLs: mergeURLs,
            outputURL: outputURL,
            outputDirectory: outputDirectory,
            splitEvery: Int(splitEvery) ?? 0,
            outputFormat: outputFormat
        )

        runner.run(request: request) { event in
            DispatchQueue.main.async {
                logs.append(event.logMessage)
                if let progress = event.progressText {
                    progressText = progress
                }
            }
        } completion: { success in
            DispatchQueue.main.async {
                isRunning = false
                if success {
                    progressText = "Done"
                } else {
                    progressText = "Failed"
                }
            }
        }
    }

    private func selectInputFile() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.begin { response in
            guard response == .OK else { return }
            inputURL = panel.url
        }
    }

    private func selectMergeFiles() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.begin { response in
            guard response == .OK else { return }
            mergeURLs = panel.urls
        }
    }

    private func selectOutputFile() {
        let panel = NSSavePanel()
        panel.canCreateDirectories = true
        panel.begin { response in
            guard response == .OK else { return }
            outputURL = panel.url
        }
    }

    private func selectOutputFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.begin { response in
            guard response == .OK else { return }
            outputDirectory = panel.url
        }
    }
}

enum Operation: String, CaseIterable, Identifiable {
    case count
    case split
    case merge
    case convert

    var id: String { rawValue }

    var title: String {
        switch self {
        case .count: return "Count"
        case .split: return "Split"
        case .merge: return "Merge"
        case .convert: return "Convert"
        }
    }
}

enum MarcFormat: String, CaseIterable, Identifiable {
    case mrc
    case mrk
    case marcxml

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .mrc: return "MRC"
        case .mrk: return "MRK"
        case .marcxml: return "MARCXML"
        }
    }
}

struct FormatDetector {
    static func detect(url: URL?) -> String? {
        guard let url else { return nil }
        let ext = url.pathExtension.lowercased()
        if ext == "mrc" { return "mrc" }
        if ext == "mrk" || ext == "txt" { return "mrk" }
        if ext == "xml" { return "marcxml" }

        guard let handle = try? FileHandle(forReadingFrom: url) else { return nil }
        defer { try? handle.close() }
        let data = handle.readData(ofLength: 2048)
        if let text = String(data: data, encoding: .utf8) {
            if text.trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("<?xml") || text.contains("<record") {
                return "marcxml"
            }
            if text.contains("=LDR") || text.range(of: "^=\\d{3}", options: .regularExpression) != nil {
                return "mrk"
            }
        }
        if data.count >= 6 {
            let prefix = data.prefix(5)
            if prefix.allSatisfy({ $0 >= 48 && $0 <= 57 }) && data.contains(0x1d) {
                return "mrc"
            }
        }
        return nil
    }
}
