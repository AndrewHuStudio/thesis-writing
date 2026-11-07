import Foundation
import Vision
import AppKit
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = false
let handler = VNImageRequestHandler(url: url)
try handler.perform([request])
for result in request.results ?? [] {
    guard let candidate = result.topCandidates(1).first else {continue}
    let box = result.boundingBox
    print(String(format:"%.3f %.3f %.3f", box.midX, 1-box.midY, candidate.confidence), candidate.string)
}
