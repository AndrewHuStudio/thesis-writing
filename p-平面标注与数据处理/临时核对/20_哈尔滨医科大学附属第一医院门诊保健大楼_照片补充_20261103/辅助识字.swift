import Foundation
import Vision
import AppKit
for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.minimumTextHeight = 0.003
    req.recognitionLanguages = ["zh-Hans", "en-US"]
    req.usesLanguageCorrection = false
    try VNImageRequestHandler(url: url).perform([req])
    let rows = (req.results ?? []).map { obs -> [String: Any] in
        let b = obs.boundingBox
        return ["text": obs.topCandidates(3).map { $0.string }, "confidence": obs.topCandidates(1).first?.confidence ?? 0, "box": [b.minX, b.minY, b.width, b.height]]
    }
    let data = try JSONSerialization.data(withJSONObject: rows, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: url.deletingPathExtension().appendingPathExtension("ocr.json"))
    print(url.lastPathComponent, rows.count)
}
