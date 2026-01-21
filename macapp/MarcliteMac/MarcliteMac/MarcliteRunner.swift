import Foundation

struct MarcliteRequest {
    let operation: Operation
    let inputURL: URL?
    let mergeURLs: [URL]
    let outputURL: URL?
    let outputDirectory: URL?
    let splitEvery: Int
    let outputFormat: MarcFormat
}

struct MarcliteEvent: Decodable {
    let event: String
    let message: String?
    let records_read: Int?
    let records: Int?
    let operation: String?

    var logMessage: String {
        if let message {
            return "[\(event)] \(message)"
        }
        if let operation {
            return "[\(event)] \(operation)"
        }
        return "[\(event)]"
    }

    var progressText: String? {
        if let records_read {
            return "Records processed: \(records_read)"
        }
        if let records {
            return "Records: \(records)"
        }
        return nil
    }
}

final class MarcliteRunner {
    func run(request: MarcliteRequest, onEvent: @escaping (MarcliteEvent) -> Void, completion: @escaping (Bool) -> Void) {
        guard let executableURL = Bundle.main.resourceURL?.appendingPathComponent("bin/marclite") else {
            onEvent(MarcliteEvent(event: "error", message: "Bundled marclite binary not found", records_read: nil, records: nil, operation: nil))
            completion(false)
            return
        }

        let process = Process()
        process.executableURL = executableURL
        process.arguments = buildArguments(for: request)

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        let stdoutHandle = stdoutPipe.fileHandleForReading
        let stderrHandle = stderrPipe.fileHandleForReading

        var stdoutBuffer = ""

        stdoutHandle.readabilityHandler = { handle in
            let data = handle.availableData
            if data.isEmpty { return }
            if let chunk = String(data: data, encoding: .utf8) {
                stdoutBuffer.append(chunk)
                while let range = stdoutBuffer.range(of: "\n") {
                    let line = String(stdoutBuffer[..<range.lowerBound])
                    stdoutBuffer.removeSubrange(..<range.upperBound)
                    guard let jsonData = line.data(using: .utf8) else { continue }
                    if let event = try? JSONDecoder().decode(MarcliteEvent.self, from: jsonData) {
                        onEvent(event)
                    } else {
                        onEvent(MarcliteEvent(event: "log", message: line, records_read: nil, records: nil, operation: nil))
                    }
                }
            }
        }

        stderrHandle.readabilityHandler = { handle in
            let data = handle.availableData
            if data.isEmpty { return }
            if let message = String(data: data, encoding: .utf8) {
                onEvent(MarcliteEvent(event: "stderr", message: message.trimmingCharacters(in: .whitespacesAndNewlines), records_read: nil, records: nil, operation: nil))
            }
        }

        process.terminationHandler = { proc in
            stdoutHandle.readabilityHandler = nil
            stderrHandle.readabilityHandler = nil
            completion(proc.terminationStatus == 0)
        }

        do {
            try process.run()
        } catch {
            onEvent(MarcliteEvent(event: "error", message: error.localizedDescription, records_read: nil, records: nil, operation: nil))
            completion(false)
        }
    }

    private func buildArguments(for request: MarcliteRequest) -> [String] {
        switch request.operation {
        case .count:
            guard let inputURL = request.inputURL else { return [] }
            return ["count", inputURL.path]
        case .split:
            guard let inputURL = request.inputURL, let outputDirectory = request.outputDirectory else { return [] }
            return ["split", "--every", String(request.splitEvery), inputURL.path, "--out-dir", outputDirectory.path]
        case .merge:
            guard let outputURL = request.outputURL else { return [] }
            var args = ["merge"]
            args.append(contentsOf: request.mergeURLs.map { $0.path })
            args.append(contentsOf: ["-o", outputURL.path, "--to", request.outputFormat.rawValue])
            return args
        case .convert:
            guard let inputURL = request.inputURL, let outputURL = request.outputURL else { return [] }
            return ["convert", inputURL.path, "-o", outputURL.path, "--to", request.outputFormat.rawValue]
        }
    }
}
